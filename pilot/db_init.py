from dotenv import load_dotenv
load_dotenv(override=True)
from database.database import create_tables, drop_tables

drop_tables()
create_tables()
