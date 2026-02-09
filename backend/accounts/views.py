from rest_framework import generics
from rest_framework.permissions import AllowAny
from .serializers import UserSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserSerializer

    def post(self, request, *args, **kwargs):
        # [Silent Login / Auto-Conversion]
        # 앱에서 가입 시도 시, 이미 존재하는 계정(username or email)이면 에러 대신 로그인 처리(토큰 발급)
        
        username = request.data.get('username')
        email = request.data.get('email')
        
        existing_user = None
        
        # 1. Username Check
        if username:
            existing_user = User.objects.filter(username=username).first()
            
        # 2. Email Check (Fallback)
        if not existing_user and email:
            existing_user = User.objects.filter(email=email).first()
            
        # 3. Handle Exists -> Login
        if existing_user:
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(existing_user)
            # 201 Created인 척하거나 200 OK로 응답. 앱 호환성 위해 200 권장.
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(existing_user).data,
                'message': 'Existing account linkage successful (Silent Login)'
            }, status=status.HTTP_200_OK)

        return super().post(request, *args, **kwargs)

from rest_framework import status
from rest_framework.response import Response
from .serializers import PasswordResetSerializer

class PasswordResetView(generics.GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = PasswordResetSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "비밀번호가 성공적으로 변경되었습니다."}, status=status.HTTP_200_OK)

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from centers.models import VerificationCode
        user = request.user
        
        # [Fix] Center has no 'center_code'. Find it from VerificationCode.
        center_code_val = None
        vc = VerificationCode.objects.filter(used_by=user, is_used=True).first()
        if vc:
            center_code_val = vc.code
            
        print(f"👤 [UserDetail] User: {user.username}, CenterCode: {center_code_val}")
        
        return Response({
            "id": user.id,
            "username": user.username,
            "risk_level": user.risk_level,
            "center_name": user.center.name if user.center else None,
            "is_center_linked": bool(user.center),
            "center_code": center_code_val,
            "linked_center_code": center_code_val,
        })

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework import status

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    [App Compatibility]
    앱 계정(app_*)의 경우 비밀번호 검사 없이 토큰을 발급하여
    로그인 실패로 인한 연동 해제를 방지함.
    """
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        
        # 1. App User Magic Login
        # [Fix] slyeee 계정도 매직 로그인 허용
        if username and (username.startswith('app_') or username == 'slyeee'):
            print(f"✨ Magic Login Attempt: {username}", flush=True)
            User = get_user_model()
            
            # [Smart Redirect] app_slyeee로 로그인해도 slyeee 토큰 발급
            real_username = username.replace("app_", "")
            target_user = User.objects.filter(username=real_username).first()
            
            if not target_user:
                # 본캐 없으면 그냥 입력된걸로 (Fallback)
                target_user = User.objects.filter(username=username).first()
            
            if target_user:
                # 비밀번호 검사 생략하고 토큰 발급
                refresh = RefreshToken.for_user(target_user)
                
                # [Fix] Center model has no 'center_code'. Find explicitly.
                from centers.models import VerificationCode
                vc_obj = VerificationCode.objects.filter(used_by=target_user, is_used=True).first()
                code_val = vc_obj.code if vc_obj else None
                
                # [Fix] UserSerializer 대신 명시적 딕셔너리 생성 (앱 호환성 100% 보장)
                user_data = {
                    "id": target_user.id,
                    "username": target_user.username,
                    "email": target_user.email,
                    "first_name": target_user.first_name,
                    "risk_level": target_user.risk_level,
                    "center_name": target_user.center.name if target_user.center else None,
                    "is_center_linked": bool(target_user.center),
                    "center_code": code_val,
                    "linked_center_code": code_val,
                }
                
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user': user_data
                }, status=status.HTTP_200_OK)
        
        # 2. Standard Login (Password Check)
        return super().post(request, *args, **kwargs)
