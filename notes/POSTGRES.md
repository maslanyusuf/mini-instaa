# Creating a PostgreSQL database

```bash
psql
CREATE USER blog WITH PASSWORD 'xxxxxx';
CREATE ROLE
CREATE DATABASE blog OWNER blog ENCODING 'UTF8';
CREATE DATABASE
```

### Dumping the existing data

```bash
python manage.py dumpdata --indent=2 --output=mysite_data.json
```

OR

```bash
python -Xutf8 manage.py dumpdata --indent=2 --output=mysite_data.json
```

### Loading the data into the new database

```bash
python manage.py loaddata mysite_data.json

```
