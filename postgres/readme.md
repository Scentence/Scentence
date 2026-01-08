# 도커-PSQL 명령어

## DB 생성
```
docker exec -it pgvector-db psql -U sentence -d postgres -c "CREATE DATABASE scentence_db;"
docker exec -it pgvector-db psql -U sentence -d postgres -c "CREATE DATABASE member_db;"
docker exec -it pgvector-db psql -U sentence -d postgres -c "CREATE DATABASE perfume_db;"
docker exec -it pgvector-db psql -U sentence -d postgres -c "CREATE DATABASE recom_db;"
```

## MEMBER_DB 테이블 생성
```
docker exec -i pgvector-db psql -U sentence -d member_db < member_db/tb_member_basic_m.sql
docker exec -i pgvector-db psql -U sentence -d member_db < member_db/tb_member_profile_t.sql
docker exec -i pgvector-db psql -U sentence -d member_db < member_db/tb_member_status_t.sql
docker exec -i pgvector-db psql -U sentence -d member_db < member_db/tb_member_visit_t.sql
```

## PERFUME_DB 테이블 생성
```
docker exec -i pgvector-db psql -U sentence -d perfume_db < perfume_db/tb_perfume_basic_m.sql
docker exec -i pgvector-db psql -U sentence -d perfume_db < perfume_db/tb_perfume_accord_m.sql
docker exec -i pgvector-db psql -U sentence -d perfume_db < perfume_db/tb_perfume_aud_m.sql
docker exec -i pgvector-db psql -U sentence -d perfume_db < perfume_db/tb_perfume_notes_m.sql
docker exec -i pgvector-db psql -U sentence -d perfume_db < perfume_db/tb_perfume_oca_m.sql
docker exec -i pgvector-db psql -U sentence -d perfume_db < perfume_db/tb_perfume_review_m.sql
docker exec -i pgvector-db psql -U sentence -d perfume_db < perfume_db/tb_perfume_season_m.sql
```

## RECOM_DB 테이블 생성
```
docker exec -i pgvector-db psql -U sentence -d recom_db < recom_db/tb_member_my_perfume_t.sql
docker exec -i pgvector-db psql -U sentence -d recom_db < recom_db/tb_member_recom_result_t.sql
```

### MEMBER_DB 데이터 적재
```
docker exec -i pgvector-db psql -U scentence -d member_db < scripts/insert/member_db/tb_member_basic_m.sql
docker exec -i pgvector-db psql -U scentence -d member_db < scripts/insert/member_db/tb_member_profile_t.sql
docker exec -i pgvector-db psql -U scentence -d member_db < scripts/insert/member_db/tb_member_status_t.sql
docker exec -i pgvector-db psql -U scentence -d member_db < scripts/insert/member_db/tb_member_visit_t.sql
```

### PERFUME_DB 데이터 적재
```
docker exec -i pgvector-db psql -U scentence -d perfume_db < scripts/insert/perfume_db/tb_perfume_basic_m.sql
docker exec -i pgvector-db psql -U scentence -d perfume_db < scripts/insert/perfume_db/tb_perfume_accord_m.sql
docker exec -i pgvector-db psql -U scentence -d perfume_db < scripts/insert/perfume_db/tb_perfume_aud_m.sql
docker exec -i pgvector-db psql -U scentence -d perfume_db < scripts/insert/perfume_db/tb_perfume_notes_m.sql
docker exec -i pgvector-db psql -U scentence -d perfume_db < scripts/insert/perfume_db/tb_perfume_oca_m.sql
docker exec -i pgvector-db psql -U scentence -d perfume_db < scripts/insert/perfume_db/tb_perfume_review_m.sql
docker exec -i pgvector-db psql -U scentence -d perfume_db < scripts/insert/perfume_db/tb_perfume_season_m.sql
```

### RECOM_DB 데이터 적재
```
docker exec -i pgvector-db psql -U scentence -d recom_db < scripts/insert/recom_db/tb_member_my_perfume_t.sql
docker exec -i pgvector-db psql -U scentence -d recom_db < scripts/insert/recom_db/tb_member_recom_result_t.sql
```

# DBeaver DB 연결 설정
```
Host: localhost
Port: 5433
Database: scentence_db
Show all databases 박스 체크
Username: scentence
Passsword: scentence
Test Connection 확인
완료
```

# 도커 명령어

## 도커 컨테이너 재시작(볼륨유지)
```
docker-compose down
docker-compose up -d --build
```

## 도커 컨테이너 재시작(볼륨삭제)
```
docker-compose down -v
docker-compose up -d --build
```

## 모든 데이터베이스 목록 확인
```
docker exec -it pgvector-db psql -U scentence -d postgres -c "\l"
```

## 특정 데이터베이스 내 테이블 목록 확인
```
docker exec -it pgvector-db psql -U scentence -d perfume_db -c "\dt"
```




``
cd postgres/scripts/perfume_db
python tables/to_csv_TB_PERFUME_BASIC_M.py
```