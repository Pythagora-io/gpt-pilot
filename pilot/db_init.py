from dotenv import load_dotenv
from database.database import create_tables, drop_tables

load_dotenv(override=True)

drop_tables()
create_tables()
