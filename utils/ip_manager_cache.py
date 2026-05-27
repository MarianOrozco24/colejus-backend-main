import time
from threading import RLock, Thread
import logging
from config.config import db
from models.ip_manager import IPRegistry
from utils.ip_location import get_ip_location
from datetime import datetime

logger = logging.getLogger(__name__)

class IPCacheManager:
    def __init__(self):
        self.ip_cache = {}  # { "ip": { "record": dict, "dirty": bool, "new": bool } }
        self.blocked_regions = {'country': set(), 'continent': set()}
        self.lock = RLock()
        self.last_sync = time.time()
        self.SYNC_INTERVAL = 600  # 10 minutos
        self.app = None

    def init_app(self, app):
        self.app = app
        self._load_regions()

    def _load_regions(self):
        with self.app.app_context():
            from models.blocked_region import BlockedRegion
            try:
                # Si la tabla recién se creó, no fallará
                regions = BlockedRegion.query.all()
                for r in regions:
                    if r.region_type == 'country':
                        self.blocked_regions['country'].add(r.region_name)
                    elif r.region_type == 'continent':
                        self.blocked_regions['continent'].add(r.region_name)
            except Exception as e:
                logger.warning(f"Error cargando regiones bloqueadas (quizá falta migrar DB): {e}")
            
            try:
                # Load all existing IPs into cache
                existing_ips = IPRegistry.query.all()
                for ip_record in existing_ips:
                    data = ip_record.to_dict()
                    data['last_seen'] = datetime.fromisoformat(data['last_seen'])
                    data['last_minute_reset'] = ip_record.last_minute_reset
                    data['last_month_reset'] = ip_record.last_month_reset
                    self.ip_cache[ip_record.ip] = {'record': data, 'dirty': False, 'new': False}
            except Exception as e:
                logger.warning(f"Error cargando el historial de IPs a caché: {e}")

    def get_or_load_ip(self, ip_address):
        if ip_address in self.ip_cache:
            return self.ip_cache[ip_address]['record']
        
        # Load from DB
        with self.lock:
            with self.app.app_context():
                ip_record = IPRegistry.query.filter_by(ip=ip_address).first()
                if ip_record:
                    data = ip_record.to_dict()
                    # Convert string dates back to datetime for internal use
                    data['last_seen'] = datetime.fromisoformat(data['last_seen'])
                    data['last_minute_reset'] = ip_record.last_minute_reset
                    data['last_month_reset'] = ip_record.last_month_reset
                    self.ip_cache[ip_address] = {'record': data, 'dirty': False, 'new': False}
                    return data
                
                # Fetch fresh location
                location_data = get_ip_location(ip_address)
                now = datetime.utcnow()
                data = {
                    'ip': ip_address,
                    'last_seen': now,
                    'requests_minute': 0,
                    'requests_month': 0,
                    'last_minute_reset': now,
                    'last_month_reset': now,
                    'pais': location_data.get('pais', 'Desconocido'),
                    'ciudad': location_data.get('ciudad', 'Desconocido'),
                    'continente': location_data.get('continente', 'Desconocido'),
                    'proveedor': location_data.get('proveedor', 'Desconocido'),
                    'dominio_proveedor': location_data.get('dominio_proveedor', 'Desconocido'),
                    'is_blocked': False
                }
                self.ip_cache[ip_address] = {'record': data, 'dirty': True, 'new': True}
                return data

    def track_request(self, ip_address):
        now = datetime.utcnow()
        with self.lock:
            record_data = self.get_or_load_ip(ip_address)
            
            # Lógica de reset por minuto
            if not record_data['last_minute_reset'] or (now - record_data['last_minute_reset']).total_seconds() > 60:
                record_data['requests_minute'] = 1
                record_data['last_minute_reset'] = now
            else:
                record_data['requests_minute'] += 1
                
            # Lógica de reset por mes
            if not record_data['last_month_reset'] or record_data['last_month_reset'].month != now.month:
                record_data['requests_month'] = 1
                record_data['last_month_reset'] = now
            else:
                record_data['requests_month'] += 1
                
            record_data['last_seen'] = now
            self.ip_cache[ip_address]['dirty'] = True

        self.check_sync()

    def check_blocked(self, ip_address):
        # Verifica si IP o su región asociada está bloqueada
        with self.lock:
            record_data = self.get_or_load_ip(ip_address)
            
            if record_data['is_blocked']:
                return True
                
            # Validar contra regiones bloqueadas
            pais = record_data.get('pais')
            continente = record_data.get('continente')
            
            if pais and pais in self.blocked_regions['country']:
                return True
            if continente and continente in self.blocked_regions['continent']:
                return True
                
        return False

    def block_ip(self, ip_address):
        with self.lock:
            record = self.get_or_load_ip(ip_address)
            record['is_blocked'] = True
            self.ip_cache[ip_address]['dirty'] = True
            # Force immediate sync for bans
            self._sync_to_db_sync()

    def unblock_ip(self, ip_address):
        with self.lock:
            record = self.get_or_load_ip(ip_address)
            record['is_blocked'] = False
            self.ip_cache[ip_address]['dirty'] = True
            self._sync_to_db_sync()

    def check_sync(self):
        if time.time() - self.last_sync > self.SYNC_INTERVAL:
            with self.lock:
                if time.time() - self.last_sync > self.SYNC_INTERVAL: # double check
                    self.last_sync = time.time()
                    Thread(target=self._sync_to_db).start()

    def _sync_to_db(self):
        with self.app.app_context():
            self._sync_to_db_sync()

    def _sync_to_db_sync(self):
        try:
            with self.lock:
                to_sync = {ip: info for ip, info in self.ip_cache.items() if info['dirty'] or info['new']}
                
                for ip, info in to_sync.items():
                    record_data = info['record']
                    if info['new']:
                        ip_record = IPRegistry(
                            ip=record_data['ip'],
                            last_seen=record_data['last_seen'],
                            requests_minute=record_data['requests_minute'],
                            requests_month=record_data['requests_month'],
                            last_minute_reset=record_data['last_minute_reset'],
                            last_month_reset=record_data['last_month_reset'],
                            pais=record_data['pais'],
                            ciudad=record_data['ciudad'],
                            continente=record_data['continente'],
                            proveedor=record_data['proveedor'],
                            dominio_proveedor=record_data['dominio_proveedor'],
                            is_blocked=record_data['is_blocked']
                        )
                        db.session.add(ip_record)
                        info['new'] = False
                    else:
                        ip_record = IPRegistry.query.filter_by(ip=ip).first()
                        if ip_record:
                            ip_record.last_seen = record_data['last_seen']
                            ip_record.requests_minute = record_data['requests_minute']
                            ip_record.requests_month = record_data['requests_month']
                            ip_record.last_minute_reset = record_data['last_minute_reset']
                            ip_record.last_month_reset = record_data['last_month_reset']
                            ip_record.is_blocked = record_data['is_blocked']
                    
                    info['dirty'] = False
                    
            db.session.commit()
            logger.info("IP cache synced to database.")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error syncing IP cache: {e}")

ip_manager_cache = IPCacheManager()
