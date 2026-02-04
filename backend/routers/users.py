from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import re
import psycopg2.extras
import psycopg2.errors
import psycopg2.errors
# [수정] database.py의 커넥션 풀 사용 (user.py 제거)
from agent.database import get_member_db_connection, release_member_db_connection, add_my_perfume
from passlib.context import CryptContext
import os
import uuid
import shutil
from datetime import datetime, timedelta
# [중복 제거] add_my_perfume은 위에서 이미 임포트됨

# 이 라우터는 '/users'로 시작하는 모든 요청을 처리합니다.
router = APIRouter(prefix="/users", tags=["users"])

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# [요청 모델] 프론트엔드(NextAuth)에서 보내주는 데이터 형식 정의
class KakaoLoginRequest(BaseModel):
    kakao_id: str  # 카카오 고유 ID (필수)
    nickname: Optional[str] = None  # NULL 허용
    email: Optional[str] = None  # NULL 허용
    profile_image: Optional[str] = None


class LocalRegisterRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None
    sex: Optional[str] = None  # 'M' or 'F'
    phone_no: Optional[str] = None
    address: Optional[str] = None
    nickname: Optional[str] = None
    user_mode: Optional[str] = None  # 'BEGINNER' or 'EXPERT'
    req_agr_yn: Optional[str] = "N"
    email_alarm_yn: Optional[str] = "N"
    sns_alarm_yn: Optional[str] = "N"


class LocalLoginRequest(BaseModel):
    email: str
    password: str


class UpdateProfileRequest(BaseModel):
    nickname: Optional[str] = None
    profile_image_url: Optional[str] = None
    name: Optional[str] = None
    sex: Optional[str] = None
    phone_no: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    sub_email: Optional[str] = None
    sns_join_yn: Optional[str] = None
    email_alarm_yn: Optional[str] = None
    sns_alarm_yn: Optional[str] = None


class UpdatePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str


# [요청 모델] 계정 연결 요청
class LinkAccountRequest(BaseModel):
    email: str                      # 기존 자체가입 계정 이메일
    password: str                   # 기존 계정 비밀번호 (검증용)
    kakao_id: str                   # 연결할 카카오 ID
    kakao_nickname: Optional[str] = None
    kakao_profile_image: Optional[str] = None


# [API] 카카오 로그인 처리 (POST /users/login)
# -----------------------------------------------------------------------------
# [로직 설명: 2026-01-28 수정됨]
# 이 함수는 카카오 로그인 요청을 받아 실제 DB에 저장된 회원 정보를 찾아 반환합니다.
#
# [핵심 변경 사항]
# 기존에는 tb_member_profile_t 테이블을 뒤져서 회원을 찾았으나, 이는 부정확했습니다.
# 이제는 tb_member_auth_t 테이블(인증 전용)을 사용하여 정확하게 회원을 식별합니다.
#
# [동작 순서]
# 1. tb_member_auth_t 조회: "카카오에서 온 이 ID(provider_user_id)를 가진 회원이 있는가?"
# 2. 존재하면 (로그인 성공): 
#    - 해당 회원의 member_id를 반환합니다.
# 3. 없으면 (신규 가입):
#    - [1단계] tb_member_basic_m: 회원 번호(ID)를 새로 발급받습니다.
#    - [2단계] tb_member_auth_t: "이 회원은 카카오 유저임"이라는 인증 정보를 저장합니다. (중요!)
#    - [3단계] tb_member_profile_t: 닉네임, 프사 등 꾸미기 정보를 저장합니다.
#    - [4단계] tb_member_status_t: 회원 상태(정상)를 저장합니다.
# -----------------------------------------------------------------------------
@router.post("/login")
def login_with_kakao(req: KakaoLoginRequest):
    # [수정] 커넥션 풀 사용
    conn = get_member_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        _ensure_profile_columns(cur)
        nickname = req.nickname or "향수초보"
        profile_image_url = req.profile_image or None

        # [STEP 1: 인증 정보 조회]
        # -------------------------------------------------------------------------
        # [수정 이유]
        # AS-IS (기존 코드): tb_member_profile_t.sns_id 컬럼을 조회했습니다.
        #                  하지만 프로필 테이블은 '정보'용이지 '인증'용이 아닙니다.
        # TO-BE (수정 코드): tb_member_auth_t 테이블을 조회합니다.
        #                  여기가 진짜 '로그인 열쇠'가 저장된 곳이기 때문입니다.
        # -------------------------------------------------------------------------
        cur.execute(
            """
            SELECT member_id
            FROM tb_member_auth_t
            WHERE provider = 'KAKAO' AND provider_user_id = %s
            """,
            (req.kakao_id,),
        )
        existing_auth = cur.fetchone()

        member_id = None

        if existing_auth:
            # [A] 이미 가입된 유저인 경우 (로그인 성공)
            member_id = existing_auth["member_id"]
            print(f"✅ 기존 회원 로그인 성공: 회원번호 {member_id}")

            status_check = _check_withdraw_status(cur, member_id)
            if status_check["status"] == "WITHDRAW_REQ":
                return {
                    "member_id": str(member_id),
                    "withdraw_pending": True,
                    "nickname": req.nickname,
                }
            if status_check["status"] == "DELETED":
                conn.commit()
                raise HTTPException(status_code=410, detail="Account deleted")

            # 프로필 정보 업데이트 (선택 사항)
            if nickname or profile_image_url:
                cur.execute(
                    "SELECT nickname, profile_image_url FROM tb_member_profile_t WHERE member_id=%s",
                    (member_id,),
                )
                profile_row = cur.fetchone()
                if profile_row:
                    if not profile_row.get("nickname") and nickname:
                        cur.execute(
                            "UPDATE tb_member_profile_t SET nickname=%s WHERE member_id=%s",
                            (nickname, member_id),
                        )
                    if not profile_row.get("profile_image_url") and profile_image_url:
                        cur.execute(
                            "UPDATE tb_member_profile_t SET profile_image_url=%s WHERE member_id=%s",
                            (profile_image_url, member_id),
                        )

        else:
            # [STEP 1.5: 이메일 중복 체크 - 계정 통합 제안]
            # -------------------------------------------------------------------------
            # [목적]
            # 카카오 로그인 시도했는데, 같은 이메일로 자체 가입된 계정이 이미 있으면
            # 자동으로 합치지 않고, "기존 계정과 연결할래?" 선택권을 줍니다.
            #
            # [보안 이유]
            # 이메일만 같다고 자동 통합하면, 타인의 계정을 뺏을 수 있습니다.
            # 반드시 비밀번호 확인 후 통합해야 합니다.
            # -------------------------------------------------------------------------
            if req.email:
                cur.execute(
                    """
                    SELECT b.member_id, p.nickname
                    FROM tb_member_basic_m b
                    JOIN tb_member_profile_t p ON b.member_id = p.member_id
                    WHERE p.email = %s AND b.join_channel = 'LOCAL'
                    """,
                    (req.email,)
                )
                existing_local_user = cur.fetchone()

                if existing_local_user:
                    # 같은 이메일로 자체 가입된 계정 발견!
                    # 프론트에 "연결 가능" 신호를 보내고, 실제 통합은 /link-account에서 처리
                    print(f"📧 이메일 중복 감지: {req.email} (기존 회원 ID: {existing_local_user['member_id']})")
                    conn.commit()
                    return {
                        "link_available": True,
                        "existing_member_id": str(existing_local_user["member_id"]),
                        "existing_nickname": existing_local_user["nickname"],
                        "email": req.email,
                        "kakao_id": req.kakao_id,
                        "kakao_nickname": nickname,
                        "kakao_profile_image": profile_image_url,
                    }

            # [STEP 2: 신규/기존 회원 판별 및 가입]
            # auth 테이블에는 없지만, 혹시 옛날 로직으로 가입된 '레거시 회원'인지 확인해야 합니다.
            # 확인 안 하고 바로 INSERT하면 login_id 중복 에러로 튕깁니다.
            
            # [2-0] 레거시 회원 확인
            cur.execute(
                """
                SELECT b.member_id 
                FROM tb_member_basic_m b
                JOIN tb_member_profile_t p ON b.member_id = p.member_id
                WHERE b.join_channel = 'KAKAO' AND p.sns_id = %s
                """,
                (req.kakao_id,)
            )
            legacy_user = cur.fetchone()

            if legacy_user:
                # [CASE A] 레거시 유저 발견! -> 마이그레이션 수행
                # -------------------------------------------------------------------------
                # [문제 상황]
                # 기존에는 tb_member_auth_t 정보만 추가하고, 프로필 정보(닉네임, 프사)는
                # 업데이트하지 않았습니다. 그래서 레거시 회원이 다시 로그인해도
                # 카카오에서 받은 최신 프로필 정보가 반영되지 않았습니다.
                #
                # [수정 내용]
                # 1. tb_member_auth_t에 인증 정보 추가 (기존 로직 유지)
                # 2. tb_member_profile_t에 닉네임, 프로필 이미지 업데이트 (신규 추가)
                #    - 기존 값이 NULL이거나 비어있을 때만 업데이트 (사용자가 직접 수정한 값 보호)
                # -------------------------------------------------------------------------
                member_id = legacy_user["member_id"]
                print(f"🔄 레거시 회원 감지 (ID: {member_id}) -> Auth 테이블 마이그레이션 수행")

                # [마이그레이션 1/2] tb_member_auth_t에 인증 정보 추가
                sql_auth_mig = """
                    INSERT INTO tb_member_auth_t
                    (member_id, provider, provider_user_id, email, created_at)
                    VALUES (%s, 'KAKAO', %s, %s, NOW())
                """
                cur.execute(sql_auth_mig, (member_id, req.kakao_id, req.email))

                # [마이그레이션 2/2] tb_member_profile_t에 프로필 정보 업데이트
                # - 닉네임: 기존 값이 NULL일 때만 카카오 닉네임으로 채움
                # - 프로필 이미지: 기존 값이 NULL일 때만 카카오 프사로 채움
                # - 이메일: 기존 값이 NULL일 때만 카카오 이메일로 채움
                if nickname or profile_image_url or req.email:
                    sql_profile_mig = """
                        UPDATE tb_member_profile_t
                        SET
                            nickname = COALESCE(NULLIF(nickname, ''), %s),
                            profile_image_url = COALESCE(NULLIF(profile_image_url, ''), %s),
                            email = COALESCE(NULLIF(email, ''), %s)
                        WHERE member_id = %s
                    """
                    cur.execute(sql_profile_mig, (nickname, profile_image_url, req.email, member_id))
                    print(f"   └─ 프로필 정보 업데이트 완료 (닉네임: {nickname}, 프사: {'있음' if profile_image_url else '없음'})")

                # 마이그레이션 완료!
                print(f"✅ 레거시 회원 마이그레이션 완료: 회원번호 {member_id}")

            else:
                # [CASE B] 진짜 신규 가입자
                # [2-1] 기본 계정 생성 (TB_MEMBER_BASIC_M)
                login_id_gen = f"kakao_{req.kakao_id}"
                sql_basic = """
                    INSERT INTO tb_member_basic_m 
                    (login_id, pwd_hash, join_channel, sns_join_yn, email_alarm_yn, sns_alarm_yn, join_dt)
                    VALUES (%s, %s, 'KAKAO', 'Y', 'N', 'N', NOW())
                    RETURNING member_id
                """
                cur.execute(sql_basic, (login_id_gen, "KAKAO_NO_PASS"))
                member_id = cur.fetchone()["member_id"]

                # [2-2] 인증 정보 저장 (TB_MEMBER_AUTH_T)
                sql_auth = """
                    INSERT INTO tb_member_auth_t
                    (member_id, provider, provider_user_id, email, created_at)
                    VALUES (%s, 'KAKAO', %s, %s, NOW())
                """
                cur.execute(sql_auth, (member_id, req.kakao_id, req.email))

                # [2-3] 프로필 정보 저장
                sql_profile = """
                    INSERT INTO tb_member_profile_t
                    (member_id, nickname, email, sns_id, profile_image_url)
                    VALUES (%s, %s, %s, %s, %s)
                """
                cur.execute(sql_profile, (member_id, nickname, req.email, req.kakao_id, profile_image_url))

                # [2-4] 상태 정보 저장
                sql_status = """
                    INSERT INTO tb_member_status_t
                    (member_id, member_status, alter_dt)
                    VALUES (%s, 'NORMAL', NOW())
                """
                cur.execute(sql_status, (member_id,))

                print(f"🎉 신규 회원가입 완료 (tb_member_auth_t 적용): 회원번호 {member_id}")





        role_type = _get_role_type(cur, member_id)
        user_mode = _get_user_mode(cur, member_id)
        conn.commit()
        return {
            "member_id": str(member_id),
            "nickname": nickname,
            "role_type": role_type,
            "user_mode": user_mode,
        }

    except Exception as e:
        conn.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        if conn:
            release_member_db_connection(conn)


# [API] 계정 연결 (POST /users/link-account)
# -----------------------------------------------------------------------------
# [목적]
# 카카오 로그인 시 같은 이메일로 자체 가입된 계정이 있을 때,
# 비밀번호 확인 후 두 계정을 하나로 통합합니다.
#
# [동작 순서]
# 1. 이메일로 자체 가입 계정 조회
# 2. 비밀번호 검증
# 3. 해당 계정의 tb_member_auth_t에 카카오 인증 정보 추가
# 4. 프로필 이미지 업데이트 (기존 값이 없을 때만)
#
# [결과]
# 통합 후 자체 로그인 + 카카오 로그인 모두 같은 member_id로 접근 가능
# -----------------------------------------------------------------------------
@router.post("/link-account")
def link_account(req: LinkAccountRequest):
    conn = get_member_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # [STEP 1] 이메일로 자체 가입 계정 조회
        cur.execute(
            """
            SELECT b.member_id, b.pwd_hash, p.nickname, p.profile_image_url
            FROM tb_member_basic_m b
            JOIN tb_member_profile_t p ON b.member_id = p.member_id
            WHERE p.email = %s AND b.join_channel = 'LOCAL'
            """,
            (req.email,)
        )
        local_user = cur.fetchone()

        if not local_user:
            raise HTTPException(status_code=404, detail="해당 이메일로 가입된 계정을 찾을 수 없습니다.")

        # [STEP 2] 비밀번호 검증
        if not pwd_context.verify(req.password, local_user["pwd_hash"]):
            raise HTTPException(status_code=401, detail="비밀번호가 일치하지 않습니다.")

        member_id = local_user["member_id"]

        # [STEP 3] 이미 카카오 연결되어 있는지 확인
        cur.execute(
            """
            SELECT auth_id FROM tb_member_auth_t
            WHERE member_id = %s AND provider = 'KAKAO'
            """,
            (member_id,)
        )
        existing_kakao = cur.fetchone()

        if existing_kakao:
            raise HTTPException(status_code=409, detail="이미 카카오 계정이 연결되어 있습니다.")

        # [STEP 4] tb_member_auth_t에 카카오 인증 정보 추가
        cur.execute(
            """
            INSERT INTO tb_member_auth_t
            (member_id, provider, provider_user_id, email, created_at)
            VALUES (%s, 'KAKAO', %s, %s, NOW())
            """,
            (member_id, req.kakao_id, req.email)
        )

        # [STEP 5] 프로필 이미지 업데이트 (기존 값이 없을 때만)
        if req.kakao_profile_image and not local_user.get("profile_image_url"):
            cur.execute(
                """
                UPDATE tb_member_profile_t
                SET profile_image_url = %s
                WHERE member_id = %s
                """,
                (req.kakao_profile_image, member_id)
            )

        conn.commit()
        print(f"🔗 계정 연결 완료: member_id={member_id}, 카카오 ID={req.kakao_id}")

        return {
            "success": True,
            "member_id": str(member_id),
            "nickname": local_user["nickname"],
            "message": "카카오 계정이 성공적으로 연결되었습니다."
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        if conn:
            release_member_db_connection(conn)


def _ensure_profile_columns(cur):
    cur.execute(
        "ALTER TABLE tb_member_profile_t ADD COLUMN IF NOT EXISTS sub_email VARCHAR(100)"
    )
    cur.execute(
        "ALTER TABLE tb_member_profile_t ADD COLUMN IF NOT EXISTS profile_image_url VARCHAR(255)"
    )


def _get_role_type(cur, member_id: int) -> str:
    try:
        cur.execute(
            "SELECT role_type FROM tb_member_basic_m WHERE member_id=%s",
            (member_id,),
        )
        row = cur.fetchone()
        if not row:
            return "USER"
        role_type = row.get("role_type")
        return (role_type or "USER").upper()
    except psycopg2.errors.UndefinedColumn:
        return "USER"


def _get_user_mode(cur, member_id: int) -> str:
    """회원의 user_mode를 조회 (챗봇 응답 스타일 결정용)"""
    try:
        cur.execute(
            "SELECT user_mode FROM tb_member_basic_m WHERE member_id=%s",
            (member_id,),
        )
        row = cur.fetchone()
        if not row:
            return "BEGINNER"
        user_mode = row.get("user_mode")
        return (user_mode or "BEGINNER").upper()
    except psycopg2.errors.UndefinedColumn:
        return "BEGINNER"


def _is_admin_member(cur, member_id: int) -> bool:
    return _get_role_type(cur, member_id) == "ADMIN"


def _ensure_admin_by_member_id(cur, member_id: int):
    if not _is_admin_member(cur, member_id):
        raise HTTPException(status_code=403, detail="Admin access required")


def _check_withdraw_status(cur, member_id: int):
    cur.execute(
        "SELECT member_status, alter_dt FROM tb_member_status_t WHERE member_id=%s",
        (member_id,),
    )
    status_row = cur.fetchone()
    if not status_row or status_row.get("member_status") != "WITHDRAW_REQ":
        return {"status": "NORMAL"}

    alter_dt = status_row.get("alter_dt")
    if alter_dt and isinstance(alter_dt, datetime):
        if alter_dt < datetime.utcnow() - timedelta(days=7):
            cur.execute(
                "DELETE FROM tb_member_basic_m WHERE member_id=%s", (member_id,)
            )
            return {"status": "DELETED"}

    return {"status": "WITHDRAW_REQ"}


def _validate_password(password: str):
    if not password:
        raise HTTPException(status_code=400, detail="Password is required")
    if len(password) < 8:
        raise HTTPException(
            status_code=400, detail="Password must be at least 8 characters"
        )
    allowed_specials_only = bool(re.fullmatch(r"[A-Za-z0-9!@#$%]+", password))
    has_lower = any(ch.islower() for ch in password)
    has_upper = any(ch.isupper() for ch in password)
    has_number = any(ch.isdigit() for ch in password)
    has_special = any(ch in "!@#$%" for ch in password)

    if not allowed_specials_only:
        raise HTTPException(
            status_code=400,
            detail="Password must use only letters, numbers, and !@#$%",
        )
    if not (has_lower and has_upper and has_number and has_special):
        raise HTTPException(
            status_code=400,
            detail="Password must include upper, lower, number, special",
        )


@router.post("/login/local")
def login_local_user(req: LocalLoginRequest):
    conn = get_member_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute(
            """
            SELECT member_id, pwd_hash, role_type, user_mode
            FROM tb_member_basic_m
            WHERE login_id=%s AND join_channel='LOCAL'
            """,
            (req.email,),
        )
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not row.get("pwd_hash"):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not pwd_context.verify(req.password, row["pwd_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        status_check = _check_withdraw_status(cur, row["member_id"])
        if status_check["status"] == "WITHDRAW_REQ":
            return {
                "member_id": str(row["member_id"]),
                "withdraw_pending": True,
            }
        if status_check["status"] == "DELETED":
            conn.commit()
            raise HTTPException(status_code=410, detail="Account deleted")

        # [추가] user_mode가 없으면 기본값 'BEGINNER'
        user_mode = row.get("user_mode")
        return {
            "member_id": str(row["member_id"]),
            "role_type": (row.get("role_type") or "USER").upper(),
            "user_mode": (user_mode or "BEGINNER").upper(), # [추가] 반환
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        if conn:
            release_member_db_connection(conn)


@router.get("/check-email")
def check_email(email: str):
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    conn = get_member_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute(
            "SELECT member_id FROM tb_member_basic_m WHERE login_id=%s", (email,)
        )
        exists = cur.fetchone() is not None
        return {"available": not exists}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        if conn:
            release_member_db_connection(conn)


@router.post("/register")
def register_local_user(req: LocalRegisterRequest):
    if req.req_agr_yn not in ("Y", "N"):
        raise HTTPException(status_code=400, detail="Invalid agreement value")

    if req.req_agr_yn != "Y":
        raise HTTPException(status_code=400, detail="Required agreements not accepted")

    if req.sex and req.sex not in ("M", "F"):
        raise HTTPException(status_code=400, detail="Invalid sex value")

    if req.email_alarm_yn not in ("Y", "N"):
        raise HTTPException(status_code=400, detail="Invalid email alarm value")

    if req.user_mode and req.user_mode not in ("BEGINNER", "EXPERT"):
        raise HTTPException(status_code=400, detail="Invalid user mode")

    password = req.password
    _validate_password(password)

    password = req.password
    _validate_password(password)

    # [수정] 커넥션 풀 사용
    conn = get_member_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute(
            "SELECT member_id FROM tb_member_basic_m WHERE login_id=%s", (req.email,)
        )
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Login ID already exists")

        pwd_hash = pwd_context.hash(password)

        sql_basic = """
            INSERT INTO tb_member_basic_m
            (login_id, pwd_hash, join_channel, sns_join_yn, email_alarm_yn, sns_alarm_yn, role_type, user_mode)
            VALUES (%s, %s, 'LOCAL', 'N', %s, %s, 'USER', %s)
            RETURNING member_id
        """
        cur.execute(sql_basic, (req.email, pwd_hash, req.email_alarm_yn, req.sns_alarm_yn, req.user_mode))
        member_id = cur.fetchone()["member_id"]

        sql_profile = """
            INSERT INTO tb_member_profile_t
            (member_id, name, nickname, sex, email, phone_no, address)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(sql_profile, (member_id, req.name, req.nickname or req.name, req.sex, req.email, req.phone_no, req.address))

        sql_status = """
            INSERT INTO tb_member_status_t
            (member_id, member_status)
            VALUES (%s, 'NORMAL')
        """
        cur.execute(sql_status, (member_id,))

        conn.commit()
        return {"member_id": str(member_id)}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        if conn:
            release_member_db_connection(conn)


@router.get("/profile/{member_id}")
def get_profile(member_id: int):
    conn = get_member_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        _ensure_profile_columns(cur)
        cur.execute(
            """
            SELECT
                b.member_id,
                b.role_type,
                b.join_channel,
                b.sns_join_yn,
                b.email_alarm_yn,
                b.sns_alarm_yn,
                p.name,
                p.nickname,
                p.sex,
                p.phone_no,
                p.address,
                p.email,
                p.sub_email,
                p.profile_image_url
            FROM tb_member_basic_m b
            LEFT JOIN tb_member_profile_t p ON b.member_id = p.member_id
            WHERE b.member_id = %s
            """,
            (member_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Member not found")
        return row
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        if conn:
            release_member_db_connection(conn)


@router.get("/nickname/check")
def check_nickname(nickname: str, member_id: Optional[int] = None):
    if not re.fullmatch(r"[A-Za-z0-9가-힣]{2,12}", nickname):
        return {"available": False}

    if not re.fullmatch(r"[A-Za-z0-9가-힣]{2,12}", nickname):
        return {"available": False}

    conn = get_member_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        _ensure_profile_columns(cur)
        if member_id:
            cur.execute(
                "SELECT member_id FROM tb_member_profile_t WHERE nickname=%s AND member_id<>%s",
                (nickname, member_id),
            )
        else:
            cur.execute(
                "SELECT member_id FROM tb_member_profile_t WHERE nickname=%s",
                (nickname,),
            )
        exists = cur.fetchone() is not None
        return {"available": not exists}
    finally:
        cur.close()
        if conn:
            release_member_db_connection(conn)


@router.patch("/profile/{member_id}")
def update_profile(member_id: int, req: UpdateProfileRequest):
    conn = get_member_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        _ensure_profile_columns(cur)

        cur.execute(
            "SELECT member_id FROM tb_member_basic_m WHERE member_id=%s",
            (member_id,),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Member not found")

        if req.sex and req.sex not in ("M", "F"):
            raise HTTPException(status_code=400, detail="Invalid sex value")

        if req.sns_join_yn and req.sns_join_yn not in ("Y", "N"):
            raise HTTPException(status_code=400, detail="Invalid sns_join_yn value")

        if req.email_alarm_yn and req.email_alarm_yn not in ("Y", "N"):
            raise HTTPException(status_code=400, detail="Invalid email_alarm_yn value")

        if req.sns_alarm_yn and req.sns_alarm_yn not in ("Y", "N"):
            raise HTTPException(status_code=400, detail="Invalid sns_alarm_yn value")

        nickname = req.nickname
        if nickname is not None:
            if not re.fullmatch(r"[A-Za-z0-9가-힣]{2,12}", nickname):
                raise HTTPException(
                    status_code=400,
                    detail="Nickname must be 2-12 chars (Korean/English/Number) with no symbols",
                )
            cur.execute(
                "SELECT member_id FROM tb_member_profile_t WHERE nickname=%s AND member_id<>%s",
                (nickname, member_id),
            )
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="Nickname already exists")

        if req.email is not None:
            cur.execute(
                "SELECT member_id FROM tb_member_basic_m WHERE login_id=%s AND member_id<>%s",
                (req.email, member_id),
            )
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="Email already exists")

        cur.execute(
            "SELECT member_id FROM tb_member_profile_t WHERE member_id=%s",
            (member_id,),
        )
        if cur.fetchone():
            cur.execute(
                """
                UPDATE tb_member_profile_t
                SET nickname = COALESCE(%s, nickname),
                    name = COALESCE(%s, name),
                    sex = COALESCE(%s, sex),
                    phone_no = COALESCE(%s, phone_no),
                    address = COALESCE(%s, address),
                    email = COALESCE(%s, email),
                    sub_email = COALESCE(%s, sub_email),
                    profile_image_url = COALESCE(%s, profile_image_url)
                WHERE member_id = %s
                """,
                (
                    req.nickname,
                    req.name,
                    req.sex,
                    req.phone_no,
                    req.address,
                    req.email,
                    req.sub_email,
                    req.profile_image_url,
                    member_id,
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO tb_member_profile_t
                (member_id, nickname, name, sex, phone_no, address, email, sub_email, profile_image_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    member_id,
                    req.nickname,
                    req.name,
                    req.sex,
                    req.phone_no,
                    req.address,
                    req.email,
                    req.sub_email,
                    req.profile_image_url,
                ),
            )

        if req.email is not None:
            cur.execute(
                """
                UPDATE tb_member_basic_m
                SET login_id = %s
                WHERE member_id = %s AND join_channel = 'LOCAL'
                """,
                (req.email, member_id),
            )

        if (
            req.email_alarm_yn in ("Y", "N")
            or req.sns_alarm_yn in ("Y", "N")
            or req.sns_join_yn in ("Y", "N")
        ):
            cur.execute(
                """
                UPDATE tb_member_basic_m
                SET email_alarm_yn = COALESCE(%s, email_alarm_yn),
                    sns_alarm_yn = COALESCE(%s, sns_alarm_yn),
                    sns_join_yn = COALESCE(%s, sns_join_yn)
                WHERE member_id = %s
                """,
                (req.email_alarm_yn, req.sns_alarm_yn, req.sns_join_yn, member_id),
            )

        conn.commit()
        return {"status": "ok"}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        if conn:
            release_member_db_connection(conn)


@router.post("/profile/{member_id}/password")
def update_password(member_id: int, req: UpdatePasswordRequest):
    if req.new_password != req.confirm_password:
        raise HTTPException(
            status_code=400, detail="Password confirmation does not match"
        )

    _validate_password(req.new_password)

    conn = get_member_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute(
            "SELECT member_id FROM tb_member_basic_m WHERE member_id=%s",
            (member_id,),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Member not found")

        cur.execute(
            "SELECT pwd_hash, join_channel FROM tb_member_basic_m WHERE member_id=%s",
            (member_id,),
        )
        row = cur.fetchone()

        if not row or not row.get("pwd_hash"):
            raise HTTPException(status_code=400, detail="Password login not enabled")

        if row.get("join_channel") != "LOCAL":
            raise HTTPException(status_code=400, detail="Password login not enabled")

        if not pwd_context.verify(req.current_password, row["pwd_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        new_hash = pwd_context.hash(req.new_password)
        cur.execute(
            """
            UPDATE tb_member_basic_m
            SET pwd_hash=%s
            WHERE member_id=%s
            """,
            (new_hash, member_id),
        )

        conn.commit()
        return {"status": "ok"}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        if conn:
            release_member_db_connection(conn)


@router.post("/profile/{member_id}/withdraw")
def request_withdraw(member_id: int):
    conn = get_member_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute(
            "SELECT member_id FROM tb_member_basic_m WHERE member_id=%s",
            (member_id,),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Member not found")

        cur.execute(
            """
            INSERT INTO tb_member_status_t (member_id, member_status)
            VALUES (%s, 'WITHDRAW_REQ')
            ON CONFLICT (member_id)
            DO UPDATE SET member_status = EXCLUDED.member_status, alter_dt = CURRENT_TIMESTAMP
            """,
            (member_id,),
        )
        conn.commit()
        return {"status": "ok"}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        if conn:
            release_member_db_connection(conn)


@router.post("/recover")
def recover_account(member_id: int):
    conn = get_member_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute(
            "SELECT member_status FROM tb_member_status_t WHERE member_id=%s",
            (member_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Member not found")

        if row.get("member_status") != "WITHDRAW_REQ":
            raise HTTPException(
                status_code=400, detail="Account is not pending withdrawal"
            )

        cur.execute(
            """
            UPDATE tb_member_status_t
            SET member_status='NORMAL', alter_dt=CURRENT_TIMESTAMP
            WHERE member_id=%s
            """,
            (member_id,),
        )
        conn.commit()
        return {"status": "ok"}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        if conn:
            release_member_db_connection(conn)


@router.post("/profile/{member_id}/image")
async def upload_profile_image(member_id: int, file: UploadFile = File(...)):
    """
    Upload profile image to S3 and save CDN URL to database.

    Process:
    1. Validate file type and size (max 5MB)
    2. Convert to 256x256 WebP
    3. Upload to S3 (profile_images/{uuid}.webp)
    4. Save CDN URL to tb_member_profile_t
    5. Delete old S3 object if it exists
    """
    from agent.image_utils import process_profile_image_upload
    from agent.storage_s3 import upload_profile_webp, parse_key_from_cdn_url, delete_key

    # Step 1: Validate and convert image
    webp_data = await process_profile_image_upload(file)

    # Step 2: Upload to S3 and get CDN URL
    try:
        s3_key, cdn_url = upload_profile_webp(webp_data)
    except Exception as e:
        import logging
        logging.error(f"S3 upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload image to storage")

    # Step 3: Update database
    conn = get_member_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        _ensure_profile_columns(cur)

        # Verify member exists
        cur.execute(
            "SELECT member_id FROM tb_member_basic_m WHERE member_id=%s",
            (member_id,),
        )
        if not cur.fetchone():
            # Clean up uploaded S3 object
            try:
                delete_key(s3_key)
            except:
                pass
            raise HTTPException(status_code=404, detail="Member not found")

        # Get existing profile image URL
        cur.execute(
            "SELECT profile_image_url FROM tb_member_profile_t WHERE member_id=%s",
            (member_id,),
        )
        existing = cur.fetchone()
        old_cdn_url = existing.get("profile_image_url") if existing else None

        # Update or insert profile image URL
        cur.execute(
            "SELECT member_id FROM tb_member_profile_t WHERE member_id=%s",
            (member_id,),
        )
        if cur.fetchone():
            cur.execute(
                """
                UPDATE tb_member_profile_t
                SET profile_image_url=%s
                WHERE member_id=%s
                """,
                (cdn_url, member_id),
            )
        else:
            cur.execute(
                """
                INSERT INTO tb_member_profile_t (member_id, profile_image_url)
                VALUES (%s, %s)
                """,
                (member_id, cdn_url),
            )

        conn.commit()

        # Step 4: Best-effort cleanup of old S3 object
        if old_cdn_url:
            old_key = parse_key_from_cdn_url(old_cdn_url)
            if old_key:
                # Only delete if it's our profile image (starts with profile_images/)
                try:
                    delete_key(old_key)
                except Exception as e:
                    import logging
                    logging.warning(f"Failed to delete old S3 object {old_key}: {e}")

        return {"profile_image_url": cdn_url}

    except HTTPException:
        conn.rollback()
        # Clean up uploaded S3 object on error
        try:
            delete_key(s3_key)
        except:
            pass
        raise
    except Exception as e:
        conn.rollback()
        # Clean up uploaded S3 object on error
        try:
            delete_key(s3_key)
        except:
            pass
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        if conn:
            release_member_db_connection(conn)


from fastapi import APIRouter, HTTPException, UploadFile, File, Header, Depends
from pydantic import BaseModel
from typing import Optional

# [Security Fix] Separate logic file import removed
# from security_deps import verify_gatekeeper_headers 

# ...

@router.get("/admin/members")
def admin_list_members(admin_member_id: int):
    conn = get_member_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        _ensure_admin_by_member_id(cur, admin_member_id)

        cur.execute(
            """
            SELECT
                b.member_id,
                p.email,
                p.nickname,
                b.join_dt,
                s.member_status,
                b.join_channel
            FROM tb_member_basic_m b
            LEFT JOIN tb_member_profile_t p ON b.member_id = p.member_id
            LEFT JOIN tb_member_status_t s ON b.member_id = s.member_id
            ORDER BY b.member_id DESC
            """
        )
        return {"members": cur.fetchall()}
    finally:
        cur.close()
        if conn:
            release_member_db_connection(conn)


@router.patch("/admin/members/{member_id}/status")
def admin_update_member_status(member_id: int, admin_member_id: int, status: str):
    if status not in ("NORMAL", "LOCK", "DORMANT", "WITHDRAW_REQ", "WITHDRAW"):
        raise HTTPException(status_code=400, detail="Invalid status")

    conn = get_member_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        _ensure_admin_by_member_id(cur, admin_member_id)

        cur.execute(
            "SELECT member_id FROM tb_member_basic_m WHERE member_id=%s",
            (member_id,),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Member not found")

        cur.execute(
            """
            INSERT INTO tb_member_status_t (member_id, member_status)
            VALUES (%s, %s)
            ON CONFLICT (member_id)
            DO UPDATE SET member_status = EXCLUDED.member_status
            """,
            (member_id, status),
        )
        conn.commit()
        return {"status": "ok"}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        if conn:
            release_member_db_connection(conn)


class SavePerfumeRequest(BaseModel):
    member_id: int  # 로그인된 사용자 ID (프론트에서 세션 정보로 보냄)
    perfume_id: int
    perfume_name: str


@router.post("/me/perfumes")
def save_my_perfume(req: SavePerfumeRequest):
    """
    사용자가 '저장하기' 버튼을 눌렀을 때 호출되는 API입니다.
    TB_MEMBER_MY_PERFUME_T 테이블에 향수를 저장합니다.
    """
    if not req.member_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    # DB 저장 함수 호출
    result = add_my_perfume(req.member_id, req.perfume_id, req.perfume_name)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    # 이미 저장된 경우도 성공(200)으로 처리하되 메시지만 다르게 줄 수 있음
    return result
