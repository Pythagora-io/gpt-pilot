from dotenv import load_dotenv
load_dotenv()
from database.database import create_tables, drop_tables

drop_tables()
create_tables()
