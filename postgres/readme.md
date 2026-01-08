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