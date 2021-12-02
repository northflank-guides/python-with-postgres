## Connect Python to Postgres

Every Python developer eventually needs to persistently store data. Many choose the popular open-source database system
Postgres. Postgres is an object-relational datastore which allows storing and querying data in a structured manner. This
blogpost introduces you how to connect your Python application to a postgres database and shows how to add, manipulate
and delete data.

### Prerequisites

- Your local machine (Python 3 and pip installed: https://www.python.org/downloads/)
    - Check with: `python --version` and `pip3 --version`. This should print the version number if successful and an
      error if the software is not installed on you machine
- An empty directory which will contain your Python project.
- A running instance of postgres with a database and user. (_link to nf: Get a free postgres instance within seconds on
  Northflank_)

> In this project, we'll use basic Python. Advanced users can use a virtual environment engine such as [venv](https://docs.python.org/3/library/venv.html), [pipenv](https://pipenv.pypa.io/) or [conda](https://conda.io). This allows you to setup clean new projects without interference from other Python projects on your machine.

### Connecting

We will be using the `psycopg2` postgres adapter for Python, one of the most established postgres libraries. Install
with: `pip3 install psycopg2`.

> There exist other postgres libraries such as `PyGreSQL`, `pg8000` or `aiopg`. The provided functionality is similar to `psycopg2`. We'll focus on `psycopg2` in this guide.

To handle sensitive connection data appropriately, we also add the `python-dotenv` package: `pip3 install python-dotenv`
. This allows us to locally load the sensitive data into environment variables. Create a file for the environment
variables `.env` in your project directory. Here we add the connection details for the postgres database:

```
PG_HOST=<postgres hostname>
PG_PORT=<postgres port>
PG_USER=<postgres database user>
PG_PASSWORD=<postgres database password>
PG_DATABASE=<database>
```

Set the variables to the values for your database.

Create a file `guide.py` in your project directory. Add following code to this file to connect to postgres and print
basic information about this postgres instance:

```python
import os
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
```

This script creates a postgres cursor which allows you to execute queries to your database. In this example, a simple
query which returns the input string is run and printed to the console.

> SSL/TLS: if your database is not running with SSL/TLS, you can remove `sslmode='require'` in the above example.

Now you're ready to run the script: `python guide.py`. This which will print a message to show that the connection to
postgres was successful. 🚀

### Adding data

Having set up the connection to postgres, we can now go on to add actual data to the database.

To add data to the database, we first need to create a table which will contain the data records. Our table will be a
simple example with three columns:

- id:   identifier which is set automatically and used to identify a record uniquely
- name: your name
- date: timestamp which will default to the date the record was added Add following lines to your script:

```python
createTableQuery = """
    CREATE TABLE IF NOT EXISTS my_table(
      id BIGSERIAL PRIMARY KEY NOT NULL ,
      name varchar,
      date TIMESTAMP NOT NULL DEFAULT current_timestamp
    );
  """
cursor.execute(createTableQuery)
```

Run it with `python guide.py`. This will create the table.
> You can run the script multiple times as it will only create the table if it doesn't exist yet.

Having added the table to the database, we can now add data. Add following lines to our script:

```python
addDataQuery = 'INSERT INTO my_table(name) VALUES(%s);'
yourName = sys.argv[1] if len(sys.argv) > 1 else 'john'  # Read your name from the command line
cursor.execute(addDataQuery, (yourName,))
```

This will execute an `INSERT` query on your previously created table, creating a new record. Run again
with: `python guide.py`. This will add your first table entry with the name `john` 🎉.

To spice things up, the script also allows you to run it with an extra argument which makes it possible to specify a
custom name: `python guide.py [name]` e.g. `python guide.py bob`.

> All command parameters are stored in an array accessible under `sys.argv`. In our example we check the length of this array to see if the argument is set.

Each time you run the script, it will add a new records to the database with the specified name.

### Reading data

To make use of the inserted data, we need to read it. To read data in postgres, usually a `SELECT` query is executed.
`SELECT` queries allow you to select the columns you want to read, filter your results and apply lots of other
operations on your read data query. In our case, we will output all columns of our table and filter records by
name (`..WHERE name =..`). Add following lines to your script:

```python
readDataQuery = 'SELECT * FROM my_table WHERE name = %s;'
cursor.execute(readDataQuery, (yourName,))
for record in cursor.fetchall():
    print(record)
```

Running the script (`python guide.py [name]`) will result in all records which match the passed name (or the default
name `john` if no name is passed) being printed to the console. You can see that the first entry (`id`) increases by one
with each new record and the third entry (`date`) matches the time of insertion.

### Cleaning up

Having created a table, inserted data and then read the data, we now know how to do all basic operations on a postgres
database in Python - almost. Don't forget to clean up!
To delete your data and the created table, we can run this command:

```python
cursor.execute('DROP TABLE IF EXISTS my_table;')
```

Add it at the end of your script and run it again: `python guide.py`.

If you run the script multiple times, you will see that only one database record is ever printed because records from
previous runs get deleted in the end.

> It's also possible to delete selected records using a `DELETE` query. E.g. `DELETE FROM my_table WHERE name = 'john';`

> If you don't want to get your data delete on every run, you can comment this line out by adding a `#` at the beginning of the line: `# cursor.execute('DROP TABLE IF EXISTS my_table;')`.

One more thing. At the end of a database connection, you should always close the cursor and connection to make sure
there is no open connection left on your postgres server. Add following lines to the end of your script:

```python
cursor.close()
connection.close()
```

### Putting it together with a webserver (optional)

In this section we will explain how to wrap our previous examples into a web server, exposing an API with different
endpoints to manipulate and read data. The web server will contain three endpoints, one for adding a
row `/write?name=<your-name>`, one for reading a row `/read?name=<your-name>` and one for deleting all data.

It makes use of the Python `http.server` package which is available by default. Create a file `main.py`:

```python
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import StringIO
from urllib.parse import urlparse, parse_qsl

import psycopg2
from dotenv import load_dotenv

load_dotenv()  # Required to load the previously defined environment variables

hostName = "0.0.0.0"
serverPort = 8080


class PostgresApiServer(BaseHTTPRequestHandler):
    def __init__(self, conn):  # Initialise server with database connection
        self.db = conn
        cursor = self.db.cursor()
        createTableQuery = """
            CREATE TABLE IF NOT EXISTS my_table(
              id BIGSERIAL PRIMARY KEY NOT NULL ,
              name varchar,
              date TIMESTAMP NOT NULL DEFAULT current_timestamp
            );
          """
        cursor.execute(createTableQuery)

    def __call__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def do_GET(self):
        try:
            cursor = self.db.cursor()  # Create db cursor which allows to execute queries on the database

            url = urlparse(self.path)
            # Parse name from URL query string, use 'john' if not set
            name = dict(parse_qsl(url.query)).get('name', 'john')
            # Handle request differently depending on URL path
            if url.path == '/read':
                readDataQuery = 'SELECT * FROM my_table WHERE name = %s;'
                cursor.execute(readDataQuery, (name,))
                records = cursor.fetchall()
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                io = StringIO()
                json.dump(records, io, indent=4, sort_keys=True, default=str)
                self.wfile.write(bytes(io.getvalue(), "utf-8"))  # Return the results as a json string
            elif url.path == '/write':
                writeDataQuery = 'INSERT INTO my_table(name) VALUES(%s);'
                cursor.execute(writeDataQuery, (name,))
                # records = cursor.fetchall()
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(bytes('{"result": "Added record with name:' + name + ' to database"}', "utf-8"))
            elif url.path == '/delete':
                deleteDataQuery = 'DROP TABLE IF EXISTS my_table;'
                cursor.execute(deleteDataQuery, (name,))
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(bytes('{"result": "Deleted all data in the table"}', "utf-8"))
            else:
                self.send_response(404)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(bytes('{"result": "path: ' + url.path + ' is not valid"}', "utf-8"))
        except Exception as e:  # Handle case where some kind of error is raised during request handling gracefully
            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(
                bytes('{"result": "some error happened while processing the request: ' + str(e) + '"}', "utf-8"))


# Create connection to postgres
connection = psycopg2.connect(host=os.environ.get('PG_HOST'),
                              port=os.environ.get('PG_PORT'),
                              user=os.environ.get('PG_USER'),
                              password=os.environ.get('PG_PASSWORD'),
                              dbname=os.environ.get('PG_DATABASE'),
                              sslmode='require')
connection.autocommit = True  # Ensure data is added to the database immediately after write commands

webServer = HTTPServer((hostName, serverPort), PostgresApiServer(connection))  # instantiate webserver

print("Listening on: http://%s:%s" % (hostName, serverPort))

# Run webserver until stopped by keyboard interrupt
try:
    webServer.serve_forever()
except KeyboardInterrupt:
    pass

# properly close webserver and db connection
webServer.server_close()
connection.close()
print("Server stopped.")
```

The server can be started with `python main.py`.

### Summary

In this how-to article, we have shown how to use Python to connect to a postgres instance and how to manipulate and read
data. We also learned how to expose this as an API with a webserver.

In a first step, a connection with a cursor is set up. This client is then used to create a database table, and records
are inserted into the table. Following, we showed how to read and filter the inserted data. Then, we demonstrated how to
remove the created data and how the close the connection properly. In the final step, the database calls are wrapped in
a web API to make it possible to access the functionality using HTTP requests.

#### Example git repository

The full source code for this example can be found in this git
repository: [https://github.com/northflank-guides/python-with-postgres](https://github.com/northflank-guides/python-with-postgres)

### Using Northflank to connect Python to Postgres for free

Northflank allows you to spin up a PostgreSQL database and a Python service within minutes. Sign up for a Northflank
account and create a free project to get started.

> [Get started here!](https://app.northflank.com/signup)

1. Make sure your project is pushed to your preferred git provider, e.g. GitHub
2. [Sign up for a free Northflank account](https://app.northflank.com/signup)
3. Create a free Northflank project
4. Within the same project, create a PostgreSQL addon
5. Create a secret group to pass your postgres secrets to your service:
    1. Select your addon in the 'Linked addons' step
    2. Select the `host`, `port`, `database`, `username` and `password` variables and add aliases for each according to
       the names [here](#connecting)
6. Within your project, create a combined service:
    1. Select your git repository and branch
    2. Select Buildpack as build type