-- insert_sample_data.sql
-- TB_MEMBER_BASIC_M 테이블에 샘플 데이터 삽입

INSERT INTO TB_MEMBER_BASIC_M (
    MEMBER_ID, 
    LOGIN_ID, 
    PWD_HASH, 
    JOIN_CHANNEL, 
    SNS_JOIN_YN, 
    REQ_AGR_YN, 
    EMAIL_ALARM_YN, 
    SNS_ALARM_YN
) VALUES
(1, 'user001', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyY5Y5Y5Y5Y', 'WEB', 'N', 'Y', 'Y', 'N'),
(2, 'user002', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyY5Y5Y5Y5Y', 'MOBILE', 'N', 'Y', 'N', 'Y'),
(3, 'user003', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyY5Y5Y5Y5Y', 'WEB', 'Y', 'Y', 'Y', 'Y'),
(4, 'user004', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyY5Y5Y5Y5Y', 'MOBILE', 'N', 'Y', 'Y', 'N'),
(5, 'user005', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyY5Y5Y5Y5Y', 'WEB', 'Y', 'Y', 'N', 'N');