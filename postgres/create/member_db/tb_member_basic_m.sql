-- MEMBER_DB / TB_MEMBER_BASIC_M
-- 회원 기본 정보 테이블

CREATE TABLE TB_MEMBER_BASIC_M (
    MEMBER_ID        BIGSERIAL      NOT NULL,                 -- 내부 식별자(PK)
    LOGIN_ID         VARCHAR(50)    NOT NULL,                 -- 로그인ID
    PWD_HASH         VARCHAR(255)   NOT NULL,                 -- 비밀번호 해시
    JOIN_CHANNEL     VARCHAR(20)    NOT NULL,                 -- 가입채널
    SNS_JOIN_YN      CHAR(1)        NOT NULL DEFAULT 'N',     -- SNS가입여부 (Y/N)
    REQ_AGR_YN       CHAR(1)        NOT NULL DEFAULT 'N',     -- 필수동의여부 (Y/N)
    EMAIL_ALARM_YN   CHAR(1)        NOT NULL DEFAULT 'N',     -- 이메일 알림 (Y/N)
    SNS_ALARM_YN     CHAR(1)        NOT NULL DEFAULT 'N',     -- 카톡/메신저 알림 (Y/N)
    JOIN_DT          TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP, -- 가입일시
    ALTER_DT         TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP, -- 수정일시

    CONSTRAINT PK_TB_MEMBER_BASIC_M
        PRIMARY KEY (MEMBER_ID),

    CONSTRAINT UK_TB_MEMBER_BASIC_M_LOGIN_ID
        UNIQUE (LOGIN_ID),

    CONSTRAINT CK_TB_MEMBER_BASIC_M_SNS_JOIN_YN
        CHECK (SNS_JOIN_YN IN ('Y', 'N')),

    CONSTRAINT CK_TB_MEMBER_BASIC_M_REQ_AGR_YN
        CHECK (REQ_AGR_YN IN ('Y', 'N')),

    CONSTRAINT CK_TB_MEMBER_BASIC_M_EMAIL_ALARM_YN
        CHECK (EMAIL_ALARM_YN IN ('Y', 'N')),

    CONSTRAINT CK_TB_MEMBER_BASIC_M_SNS_ALARM_YN
        CHECK (SNS_ALARM_YN IN ('Y', 'N'))
);