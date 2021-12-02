import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()  # Required to load the previously defined environment variables

# Create connection to postgres
connection = psycopg2.connect(host=os.environ.get('PG_HOST'),
                              port=os.environ.get('PG_PORT'),
                              user=os.environ.get('PG_USER'),
                              password=os.environ.get('PG_PASSWORD'),
                              dbname=os.environ.get('PG_DATABASE'),
                              sslmode='require')
connection.autocommit = True  # Ensure data is added to the database immediately after write commands
cursor = connection.cursor()
cursor.execute('SELECT %s as connected;', ('Connection to postgres successful!',))
print(cursor.fetchone())

createTableQuery = """
    CREATE TABLE IF NOT EXISTS my_table(
      id BIGSERIAL PRIMARY KEY NOT NULL ,
      name varchar,
      date TIMESTAMP NOT NULL DEFAULT current_timestamp
    );
  """
cursor.execute(createTableQuery)

addDataQuery = 'INSERT INTO my_table(name) VALUES(%s);'
yourName = sys.argv[1] if len(sys.argv) > 1 else 'john'  # Read your name from the command line
cursor.execute(addDataQuery, (yourName,))

readDataQuery = 'SELECT * FROM my_table WHERE name = %s;'
cursor.execute(readDataQuery, (yourName,))
for record in cursor.fetchall():
    print(record)

cursor.execute('DROP TABLE IF EXISTS my_table;')

cursor.close()
connection.close()
