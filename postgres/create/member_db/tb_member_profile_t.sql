-- MEMBER_DB / TB_MEMBER_PROFILE_T
-- 회원 프로필 정보 테이블

CREATE TABLE TB_MEMBER_PROFILE_T (
    MEMBER_ID   BIGINT        NOT NULL,                 -- 내부 식별자 (회원ID)
    NAME        VARCHAR(50),                             -- 이름
    SEX         CHAR(1),                                 -- 성별
    PHONE_NO    VARCHAR(20),                             -- 핸드폰번호
    NICKNAME    VARCHAR(50),                             -- 닉네임
    ADDRESS     VARCHAR(255),                            -- 주소
    EMAIL       VARCHAR(100),                            -- 이메일
    SNS_ID      VARCHAR(100),                            -- 카톡ID
    ALTER_DT    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP, -- 개인정보 수정일시

    CONSTRAINT PK_TB_MEMBER_PROFILE_T
        PRIMARY KEY (MEMBER_ID),

    CONSTRAINT FK_TB_MEMBER_PROFILE_T_MEMBER
        FOREIGN KEY (MEMBER_ID)
        REFERENCES TB_MEMBER_BASIC_M (MEMBER_ID),

    CONSTRAINT CK_TB_MEMBER_PROFILE_T_SEX
        CHECK (SEX IN ('M', 'F'))
);
