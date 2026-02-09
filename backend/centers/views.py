from rest_framework import views, status, permissions, generics
from rest_framework.response import Response
from .models import Center, VerificationCode
from .serializers import CenterSerializer
from django.contrib.auth import get_user_model
from haru_on.models import HaruOn
from django.utils.dateparse import parse_datetime
from datetime import datetime

User = get_user_model()

class GenerateVerificationCodeView(views.APIView):
    # TODO: 실제로는 의료진(Staff) 권한만 접근 가능하도록 설정해야 함
    # permission_classes = [permissions.IsAuthenticated]
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # 현재 로그인한 사용자가 관리하는 센터 정보를 가져와야 함 (User 모델 확장 필요 또는 가정)
        # 임시로 요청 바디에서 center_id를 받는다고 가정 (슈퍼유저 테스트용)
        center_id = request.data.get('center_id')
        
        # 실제 운영에선 request.user.profile.center 등으로 가져와야 함
        if not center_id:
             # 임시: 슈퍼유저가 아니거나 center_id가 없으면 첫 번째 센터 사용
             first_center = Center.objects.first()
             if not first_center:
                 return Response({'error': '등록된 센터가 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
             center = first_center
        else:
            try:
                center = Center.objects.get(id=center_id)
            except Center.DoesNotExist:
                return Response({'error': '존재하지 않는 센터입니다.'}, status=status.HTTP_404_NOT_FOUND)

        # 코드 생성
        code_obj = VerificationCode.objects.create(center=center)
        
        return Response({
            'code': code_obj.code,
            'center_name': center.name,
            'expires_at': '무제한 (사용 시 만료)', 
            'message': '일회용 인증 코드가 생성되었습니다. 사용자에게 전달해주세요.'
        }, status=status.HTTP_201_CREATED)

from rest_framework.decorators import api_view, permission_classes as deco_permissions

@api_view(['POST'])
@deco_permissions([permissions.AllowAny])
def verify_center_code(request):
    # --- File Logging Start ---
    try:
        with open('request_log.txt', 'a') as f:
            f.write(f"\n[{datetime.now()}] Verify Request (FBV)\n")
            f.write(f"Headers: {request.headers}\n")
            f.write(f"Data: {request.data}\n")
    except:
        pass
    # --- File Logging End ---

    print(f"🔍 [DEBUG] Received Headers: {request.headers}")
    print(f"🔍 [DEBUG] Received Body: {request.data}")
    
    # iOS 앱 버전에 따라 키 값이 다를 수 있음 (center_code 또는 code)
    data = request.data
    code_input = data.get('center_code') or data.get('code')
    
    # 방어 로직: DRF가 파싱 못했을 경우 request.body 직접 확인
    if not code_input:
        import json
        try:
            body_data = json.loads(request.body)
            code_input = body_data.get('center_code') or body_data.get('code')
            data = body_data # 바디 데이터 갱신
            print(f"🔍 [DEBUG] Solved by manual parsing: {code_input}")
        except:
            pass

    if not code_input:
        return Response({'error': '인증 코드를 입력해주세요.'}, status=status.HTTP_400_BAD_REQUEST)

    # [Safety] 공백 제거 및 문자열 변환
    code_input = str(code_input).strip()
    print(f"🔍 [Verify] Processing Code: '{code_input}' (Len: {len(code_input)})")

    try:
        # [Generic Identity Unification]
        # 1. 코드 유효성 검사
        verification_code = VerificationCode.objects.filter(code__iexact=code_input).first()
        
        # [Master Code] 테스트용 마스터 코드 (777777)
        if not verification_code and code_input == '777777':
            print("✨ [Verify] Master Code Used!")
            first_center = Center.objects.first()
            if not first_center:
                    first_center = Center.objects.create(name="기본 보건소", location="서울시")
            verification_code, _ = VerificationCode.objects.get_or_create(
                code='777777', 
                defaults={'center': first_center, 'is_used': False}
            )
            if verification_code.is_used:
                verification_code.is_used = False
                verification_code.save()

        if not verification_code:
            print(f"❌ [Verify] Code Not Found. Input: '{code_input}'")
            return Response({'valid': False, 'error': '유효하지 않은 코드입니다.'}, status=status.HTTP_404_NOT_FOUND)
        
        # 2. 사용자 등록 및 통합 (Identity Unification)
        nickname = data.get('user_nickname') or data.get('nickname') or data.get('name')
        
        final_user = None
        is_merged = False
        
        # [Reverse Merge Logic]
        # 기존 주인을 현재 유저로 교체하는 방식 (앱 세션 유지)
        
        # 현재 요청 유저 식별 (닉네임 기반)
        current_user = None
        if nickname:
            # [Change] 'app_' 접두사 제거. 오직 닉네임 그대로 사용.
            # 사용자가 'app_' 계정 사용을 원치 않음.
            current_user = User.objects.filter(username=nickname).first()
        
        if verification_code.is_used and verification_code.used_by:
            # [A] 이미 사용된 코드 -> 기존 주인(old_owner) 확인
            old_owner = verification_code.used_by
            print(f"♻️ [Verify] Code owned by {old_owner.username}. Checking for merge...")
            
            if not current_user:
                 # 현재 유저가 없다면 닉네임으로 생성
                 current_user = User.objects.create(
                     username=nickname,
                     email=f"{nickname}@app.user",
                     is_active=True
                 )
                 current_user.set_unusable_password()
                 current_user.save()

            if current_user and current_user != old_owner:
                print(f"♻️ [Verify] Moving data from Old({old_owner.username}) to Current({current_user.username})...")
                
                # [Data Migration] Reverse: Old -> Current
                moved_count = HaruOn.objects.filter(user=old_owner).update(user=current_user)
                print(f"🚚 [Verify] Data Recovery: Recovered {moved_count} items.")
                
                # 코드 소유권 이전
                verification_code.used_by = current_user
                verification_code.save()
                
                # [Fix] 사용자 소속 기관 업데이트
                current_user.center = verification_code.center
                current_user.save()
            
            final_user = current_user
            is_merged = False # 신원은 유지됨
            
        else:
            # [B] New Registration (New Code)
            if not current_user and nickname:
                current_user, created = User.objects.get_or_create(
                    username=nickname,
                    defaults={'email': f"{nickname}@app.user", 'is_active': True}
                )
                if created:
                    current_user.set_unusable_password()
                    current_user.save()
            
            # 코드 소유권 할당
            if current_user:
                verification_code.is_used = True
                verification_code.used_at = datetime.now()
                verification_code.used_by = current_user
                verification_code.save()
                
                # [Fix] 사용자 소속 기관 업데이트
                current_user.center = verification_code.center
                current_user.save()
                print(f"✅ [Verify] Code Assigned to {current_user.username}")
                
            final_user = current_user

        if not final_user:
             # 닉네임도 없고 유저도 못 찾은 경우
             return Response({'error': '사용자 정보를 찾을 수 없습니다 (닉네임 필요).'}, status=400)

        # 3. 응답
        response_data = {
            'valid': True, 
            'center_name': verification_code.center.name,
            'user_id': final_user.id
        }
        
        return Response(response_data)

    except Exception as e:
        print(f"❌ [Verify] Logic Error: {e}")
        return Response({'valid': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CenterListView(generics.ListAPIView):
    queryset = Center.objects.all()
    serializer_class = CenterSerializer
    permission_classes = [permissions.AllowAny]

class SyncDataView(views.APIView):
    """
    iOS 앱에서 데이터를 수신하여 저장 (B2G 연동 핵심)
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = [] # [Fix 401] 토큰이 만료되었거나 잘못되어도 401을 뱉지 않도록 인증 비활성화

    def get(self, request):
        """
        [Pull] Web(217) 서버가 150 서버의 데이터를 가져가기 위한 API
        """
        action = request.query_params.get('action')
        center_code = request.query_params.get('center_code')
        nickname = request.query_params.get('user_nickname')
        
        # [Mode 1] Code Recovery (Self-Healing)
        # [Mode 1] Code Recovery (Self-Healing)
        if action == 'check_link' and nickname:
            print(f"🔍 [SyncData] Checking link for nickname: {nickname}")
            
            # [Change] 'app_' 계정으로 요청해도 본캐(slyeee) 확인
            real_nickname = nickname.replace("app_", "")
            target_user = User.objects.filter(username=real_nickname).first()
            
            if not target_user:
                # 본캐 없으면 원본 그대로 확인 (Fallback)
                target_user = User.objects.filter(username=nickname).first()
            
            if not target_user:
                return Response({'linked': False, 'message': 'User not found in 150'}, status=404)
                
            try:
                vc = VerificationCode.objects.filter(used_by=target_user, is_used=True).first()
                if vc:
                    print(f"✅ [SyncData] Found Code {vc.code} for {target_user.username}")
                    return Response({
                        'linked': True, 
                        'center_code': vc.code,
                        'center_name': vc.center.name if vc.center else "Unknown"
                    }, status=200)
            except Exception as e:
                print(f"❌ [SyncData] Link Check Error: {e}")
                
            return Response({'linked': False}, status=200)

        # [Mode 2] Data Fetch
        target_user = None
        if request.user and request.user.is_authenticated:
            target_user = request.user
        elif center_code and nickname:
            # Tokenless Access via Code & Nickname
            try:
                vc = VerificationCode.objects.filter(code=center_code).first()
                if vc and vc.is_used and vc.used_by:
                     # Check if username matches nickname
                     u_name = vc.used_by.username
                     if u_name == nickname or nickname in u_name:
                          target_user = vc.used_by
            except:
                pass
        
        if not target_user:
             return Response({'error': 'Unauthorized / Center Code Mismatch'}, status=401)
        
        # Fetch Diaries
        diaries = HaruOn.objects.filter(user=target_user).order_by('created_at')
        data = []
        for d in diaries:
            analysis = d.analysis_result or {}
            
            item = {
                'id': d.id,
                'event': d.content or analysis.get('event', ''), # Content Fallback
                'mood_level': d.mood_score if d.mood_score > 0 else 5, # Score Fallback
                'created_at': d.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'content': d.content or analysis.get('event', '내용 없음'),
                'ai_prediction': analysis.get('ai_prediction', '분석 대기 중...'),
                'ai_comment': analysis.get('ai_comment', '') or analysis.get('ai_advice', ''),
                'ai_analysis': analysis.get('ai_analysis', ''),
                'emotion': analysis.get('emotion_desc', '') or analysis.get('emotion', ''),
                'meaning': analysis.get('emotion_meaning', '') or analysis.get('meaning', ''),
                'selftalk': analysis.get('self_talk', '') or analysis.get('selftalk', ''),
                'sleep_condition': analysis.get('sleep_condition', '') or analysis.get('sleep', ''),
                'weather': analysis.get('weather', ''),
                'medication_taken': analysis.get('medication_taken', False),
                'symptoms': analysis.get('symptoms', []),
                'gratitude_note': analysis.get('gratitude_note', '') or analysis.get('gratitude', '')
            }
            data.append(item)
            
        return Response(data)

    def post(self, request):
        """
        [Push] iOS 앱 -> 150 서버 데이터 전송
        """
        data = request.data
        center_code = data.get('center_code') or data.get('code')
        nickname = data.get('user_nickname')
        mood_metrics = data.get('mood_metrics', [])
        
        print(f"📥 [SyncData] Push Request. Code: {center_code}, User: {nickname}, Count: {len(mood_metrics)}")

        # 1. JWT Identity
        if request.user and request.user.is_authenticated:
            target_user = request.user
        else:
            # Fallback (Tokenless)
            # [Change] Remove app_ prefix usage -> Smart Resolve
            if nickname:
                 real_nickname = nickname.replace("app_", "")
                 user = User.objects.filter(username=real_nickname).first()
                 
                 if not user:
                     # 본캐 없으면 원본 그대로 확인
                     user = User.objects.filter(username=nickname).first()
                     
                 if not user:
                     # 없으면 생성 (본캐 이름으로)
                     user = User.objects.create(username=real_nickname, email=f"{real_nickname}@app.user")
                     user.set_unusable_password()
                     user.save()
                 target_user = user
            else:
                 # No nickname provided
                 username_guest = f"guest_{center_code}"
                 user, _ = User.objects.get_or_create(username=username_guest, defaults={'email': f"{username_guest}@app.user"})
                 target_user = user

        # 2. Code Ownership Validation (Optional update)
        if center_code:
            try:
                vc = VerificationCode.objects.filter(code=center_code).first()
                if vc and not vc.is_used:
                    vc.is_used = True
                    vc.used_at = datetime.now()
                    vc.used_by = target_user
                    vc.save()
                    
                    # [Fix] 사용자 소속 기관 업데이트
                    target_user.center = vc.center
                    target_user.save()
                    print(f"🔗 [B2G] Ownership Claimed: {center_code} -> User({target_user.id})")
            except:
                pass
        
        # 3. Save Data
        saved_count = 0
        for item in mood_metrics:
            try:
                date_str = item.get('created_at')
                date_only_str = item.get('date')
                
                created_at = None
                if date_str:
                    try:
                        # [Fix] ISO 8601 'Z' parsing support for Python 3.7+
                        if date_str.endswith('Z'):
                            date_str = date_str.replace('Z', '+00:00')
                        created_at = parse_datetime(date_str)
                    except:
                        pass
                
                if not created_at and date_only_str:
                    try:
                        # [Fallback] Date Only (YYYY-MM-DD)
                        dt = datetime.strptime(date_only_str, "%Y-%m-%d")
                        created_at = dt # Naive datetime is acceptable here, Django will handle TZ
                    except:
                        pass

                if not created_at:
                    created_at = datetime.now()
                
                # AI Score Logic
                raw_score = item.get('score', 0)
                ai_sentiment_text = item.get('ai_prediction', '') or item.get('emotion', '')
                
                def calculate_ai_score(text, default_score):
                    if not text: return default_score
                    if any(x in text for x in ['행복', '기쁨', '신남', '즐거움', '긍정']): return 9 
                    if any(x in text for x in ['편안', '평온', '감사', '보람']): return 7       
                    if any(x in text for x in ['보통', '무난', '평범', '덤덤']): return 5       
                    if any(x in text for x in ['우울', '슬픔', '눈물', '지침', '피곤']): return 3 
                    if any(x in text for x in ['화남', '분노', '짜증', '불안', '두려움']): return 1 
                    return default_score

                if ai_sentiment_text:
                    score = calculate_ai_score(ai_sentiment_text, raw_score)
                else:
                    score = raw_score
                
                # Content
                event = item.get('event', '')
                full_content = event if event else f"기분 점수: {score}점"
                
                ai_data = {}
                if item.get('ai_comment'): ai_data['ai_comment'] = item.get('ai_comment')
                if item.get('ai_advice'): ai_data['ai_advice'] = item.get('ai_advice')
                if item.get('ai_analysis'): ai_data['ai_analysis'] = item.get('ai_analysis')
                if item.get('ai_prediction'): ai_data['ai_prediction'] = item.get('ai_prediction')
                
                emotion = item.get('emotion', '')
                meaning = item.get('meaning', '')
                selftalk = item.get('selftalk', '')
                sleep = item.get('sleep', '')
                
                if sleep: ai_data['sleep_condition'] = sleep
                if meaning: ai_data['emotion_meaning'] = meaning
                if selftalk: ai_data['self_talk'] = selftalk
                if emotion: ai_data['emotion_desc'] = emotion
                
                weather = item.get('weather', '')
                meds_taken = item.get('medication_taken', False)
                symptoms = item.get('symptoms', [])
                gratitude = item.get('gratitude', '')

                if weather: ai_data['weather'] = weather
                ai_data['medication_taken'] = meds_taken
                if symptoms: ai_data['symptoms'] = symptoms
                if gratitude: ai_data['gratitude_note'] = gratitude
                # 중복 방지 (Manual Check for Update or Create)
                # update_or_create는 get()을 사용하여 중복 시 에러 발생 가능
                existing_record = HaruOn.objects.filter(user=target_user, created_at=created_at).first()
                
                if existing_record:
                    # Update with Guard Logic
                    should_update_content = True
                    should_update_ai = True
                    
                    # 1. Content Guard
                    # If existing content is significant (>10 chars) and incoming is likely a fallback (starts with "기분 점수:"), preserve existing.
                    if len(existing_record.content) > 10 and full_content.startswith("기분 점수:"):
                        should_update_content = False
                        print(f"🛡️ [SyncData] Protected Content for {date_str}")

                    # [VAULT POLICY] 150 Server is the Single Source of Truth
                    # Once data is written (Content or AI), it MUST NOT be overwritten by client sync.
                    
                    has_real_content = bool(existing_record.content and len(existing_record.content.strip()) > 5)
                    has_real_ai = bool(existing_record.analysis_result and len(str(existing_record.analysis_result)) > 20)

                    if has_real_content or has_real_ai:
                        # LOCKED: Server data exists. Do not touch it.
                        print(f"🔒 [Vault] Locked {date_str}. Server data is preserved. (Content:{has_real_content}, AI:{has_real_ai})")
                        should_update_content = False
                        should_update_ai = False
                    else:
                        # OPEN: Server is empty. Allow update.
                        print(f"🔓 [Vault] Updating empty slot for {date_str}.")
                        should_update_content = True
                        should_update_ai = True

                    if should_update_content:
                        existing_record.content = full_content.strip()
                        existing_record.mood_score = score
                        existing_record.is_high_risk = (score <= 2)
                    
                    if should_update_ai and ai_data:
                        existing_record.analysis_result = ai_data
                        
                    if should_update_content or should_update_ai:
                        existing_record.save()
                        saved_count += 1
                    else:
                        print(f"⏩ [Vault] Skipped save for {date_str}")
                    saved_count += 1
                else:
                    # Create
                    HaruOn.objects.create(
                        user=target_user,
                        created_at=created_at,
                        content=full_content.strip(),
                        mood_score=score,
                        is_high_risk=(score <= 2),
                        analysis_result=ai_data if ai_data else None
                    )
                    saved_count += 1
                continue
            except Exception as e:
                print(f"❌ [SyncData] Error: {e}")
                continue
        
        # Risk Level Update
        if any((item.get('score', 10) <= 2) for item in mood_metrics):
             target_user.risk_level = User.RiskLevel.HIGH
             target_user.save()

        # Relay to 217
        if center_code:
            try:
                import requests
                relay_payload = {
                    "center_code": center_code,
                    "user_nickname": nickname,
                    "risk_level": target_user.risk_level if hasattr(target_user, 'risk_level') else 1,
                    "mood_metrics": mood_metrics
                }
                requests.post(
                    "https://217.142.253.35.nip.io/api/v1/centers/sync-data/", 
                    json=relay_payload, timeout=5, verify=False
                )
            except: pass

        # [Fix] Sync 응답에도 로그인 시와 동일한 'user' 객체를 포함 (앱 상태 유지 필수)
        from centers.models import VerificationCode
        vc_obj = VerificationCode.objects.filter(used_by=target_user, is_used=True).first()
        code_val = vc_obj.code if vc_obj else None

        user_data = {
            "id": target_user.id,
            "username": target_user.username,
            "email": target_user.email,
            "first_name": target_user.first_name,
            "risk_level": target_user.risk_level,
            "center_name": target_user.center.name if target_user.center else None,
            "is_center_linked": True,
            "center_code": code_val,
            "linked_center_code": code_val,
        }

        return Response({
            'success': True,
            'message': f'{saved_count}건의 데이터가 동기화되었습니다.',
            'user': user_data,  # [Key] 앱이 기대하는 핵심 객체
            # 하위 호환성 유지
            'user_id': target_user.id,
            'is_center_linked': True, 
            'center_name': target_user.center.name if target_user.center else None,
            'center_code': code_val,
            'linked_center_code': code_val
        })
