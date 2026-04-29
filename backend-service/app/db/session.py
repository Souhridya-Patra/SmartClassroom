import os
import time

import mysql.connector
from mysql.connector import Error


def get_connection(max_retries: int = 10, retry_delay_seconds: int = 2):
    host = os.getenv("DB_HOST", "db")
    port = int(os.getenv("DB_PORT", "3306"))
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    database = os.getenv("DB_NAME", "smart_classroom")

    candidate_hosts = [host]
    if host != "db":
        candidate_hosts.append("db")

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        for candidate_host in candidate_hosts:
            try:
                connection = mysql.connector.connect(
                    host=candidate_host,
                    port=port,
                    user=user,
                    password=password,
                    database=database,
                )
                if connection.is_connected():
                    return connection
            except Error as exc:
                last_error = exc

        if attempt < max_retries:
            time.sleep(retry_delay_seconds)

    raise RuntimeError(f"Unable to connect to MySQL after {max_retries} attempts: {last_error}")
