# logger_config.py
import logging
import os
import sys
from datetime import datetime

def setup_logger(name='manager_positions_logger', log_dir='logs'):
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Verifica se o logger já possui handlers para evitar duplicidade
    if not logger.handlers:
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')

        # Console handler com encoding UTF-8
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        
        # Tentar forçar encoding UTF-8 no console (pode não funcionar em todos os sistemas)
        try:
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass
            
        logger.addHandler(ch)

        # File handler com encoding UTF-8
        today = datetime.now().strftime('%Y%m%d')
        log_filename = os.path.join(log_dir, f'{name}_{today}.log')
        fh = logging.FileHandler(log_filename, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    
    return logger