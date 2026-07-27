import logging
import os
import sys
from config import paths

def setup_logger(name="JARVISH"):
    logger = logging.getLogger(name)
    
    # If logger already has handlers, return it to avoid duplicate logs
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File Handler
    try:
        user_dir = paths.USER_DIR
        logs_dir = os.path.join(user_dir, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(os.path.join(logs_dir, "jarvish.log"))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to setup file logger: {e}")
        
    return logger

logger = setup_logger()
