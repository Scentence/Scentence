-- file: tb_member_basic_m.sql

CREATE TABLE TB_MEMBER_BASIC_M (
    MEMBER_ID        INT            PRIMARY KEY,
    LOGIN_ID         VARCHAR(50)     NOT NULL,
    PWD_HASH         VARCHAR(255)    NOT NULL,
    JOIN_CHANNEL     VARCHAR(20),
    SNS_JOIN_YN      CHAR(1)         DEFAULT 'N',
    REQ_AGR_YN       CHAR(1)         DEFAULT 'N',
    EMAIL_ALARM_YN   CHAR(1)         DEFAULT 'N',
    SNS_ALARM_YN     CHAR(1)         DEFAULT 'N',
    JOIN_DT          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ALTER_DT         TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 선택적 인덱스 (로그인 기준 조회 대비)
-- CREATE UNIQUE INDEX IDX_TB_MEMBER_BASIC_M_LOGIN_ID
--     ON TB_MEMBER_BASIC_M (LOGIN_ID);
