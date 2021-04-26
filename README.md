# Minimon
- A miniture monitor that can actually do a lot of monitoring

DOcker
docker run -dit --name minimon-postgres -e POSTGRES_PASSWORD=secret -d postgres
docker exec -it -e PGPASSWORD=secret minimon-postgres pg_dump -U postgres -h 172.17.0.3 -d minimon > schema.sql
psql -U postgres -W -h 172.17.0.3 -d minimon
