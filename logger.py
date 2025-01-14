import logging
import os
from datetime import datetime

# Create the "_log" directory if it doesn't exist
log_directory = "_logs"
os.makedirs(log_directory, exist_ok=True)

# Generate the log file name using the current date
log_file = os.path.join(log_directory, f"{datetime.now().strftime('%Y-%m-%d')}.log")

# Configure the logger
logging.basicConfig(
    filename=log_file,  # Log file path
    filemode="a",       # Append mode
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO  # Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
)

# Create a logger object
logger = logging.getLogger("VTKImageLabeler")

# Optional: Set the logger level explicitly if needed
logger.setLevel(logging.DEBUG)  # Adjust to desired log level
