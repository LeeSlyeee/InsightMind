<script setup>
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const router = useRouter();
const authStore = useAuthStore();

const goLogin = () => {
  router.push('/login');
};

const goDashboard = () => {
  if (authStore.isAuthenticated) {
    router.push('/admin/dashboard');
  } else {
    alert('로그인이 필요합니다.');
    router.push('/login');
  }
};
</script>

<template>
  <main class="flex min-h-screen flex-col items-center justify-center bg-slate-50 p-6">
    <div class="text-center w-full max-w-2xl">
      <h1 class="mb-2 text-4xl font-extrabold text-blue-900 tracking-tight">Maum-On Staff Portal</h1>
      <p class="mb-10 text-lg text-slate-600 font-medium">보건소/정신건강복지센터 담당자 전용 시스템</p>
      
      <div class="rounded-xl bg-white p-10 shadow-xl border border-slate-100">
        <div v-if="authStore.isAuthenticated" class="space-y-6">
            <div class="bg-blue-50 p-4 rounded-lg">
                <p class="text-blue-800 font-bold text-lg mb-1">
                    {{ authStore.user?.username || '관리자' }}님
                </p>
                <p class="text-blue-600 text-sm">현재 접속 중입니다.</p>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <button 
                  @click="goDashboard" 
                  class="flex items-center justify-center h-16 rounded-lg bg-blue-600 font-bold text-white hover:bg-blue-700 transition shadow-md hover:shadow-lg"
                >
                  📊 통합 대시보드 입장
                </button>
                <button 
                  @click="authStore.logout" 
                  class="flex items-center justify-center h-16 rounded-lg bg-slate-200 font-bold text-slate-700 hover:bg-slate-300 transition"
                >
                  로그아웃
                </button>
            </div>
        </div>

        <div v-else class="space-y-6">
            <p class="text-slate-500">
                의료진 및 센터 담당자는 승인된 계정으로 로그인해 주세요.
            </p>
            <button 
              @click="goLogin" 
              class="w-full rounded-lg bg-blue-600 px-6 py-4 text-lg font-bold text-white hover:bg-blue-700 transition shadow-lg"
            >
              담당자 로그인
            </button>
        </div>
      </div>
      
      <p class="mt-8 text-xs text-slate-400">
          본 시스템은 인가된 의료진 및 담당자만 접근 가능합니다. <br>
          무단 접속 시 법적 처벌을 받을 수 있습니다.
      </p>
    </div>
  </main>
</template>
