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
