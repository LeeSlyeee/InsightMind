<script setup>
import { ref } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router';

const username = ref('');
const password = ref('');
const errorMsg = ref('');
const authStore = useAuthStore();
const router = useRouter();

// 비밀번호 찾기 모달 관련
const showResetModal = ref(false);
const resetForm = ref({
    username: '',
    first_name: '',
    new_password: ''
});
const resetMsg = ref('');
const resetSuccess = ref(false);

const handleLogin = async () => {
    try {
        await authStore.login(username.value, password.value);
        router.push('/');
    } catch (err) {
        errorMsg.value = '로그인에 실패했습니다. 아이디와 비밀번호를 확인해주세요.';
    }
};

const handleResetPassword = async () => {
    resetMsg.value = '';
    resetSuccess.value = false;
    try {
        await authStore.resetPassword(resetForm.value);
        resetSuccess.value = true;
        resetMsg.value = '비밀번호가 성공적으로 변경되었습니다.';
        setTimeout(() => {
            showResetModal.value = false;
            resetForm.value = { username: '', first_name: '', new_password: '' };
            resetMsg.value = '';
        }, 2000);
    } catch (err) {
        resetSuccess.value = false;
        resetMsg.value = err.response?.data?.message || err.response?.data?.non_field_errors?.[0] || '정보가 일치하지 않거나 오류가 발생했습니다.';
    }
};
</script>

<template>
    <div class="flex min-h-screen flex-col items-center justify-center bg-gray-100 p-4">
        <div class="w-full max-w-md rounded-lg bg-white p-8 shadow-md">
            <h2 class="mb-6 text-center text-2xl font-bold text-gray-800">로그인</h2>
            
            <form @submit.prevent="handleLogin" class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700">아이디</label>
                    <input 
                        v-model="username" 
                        type="text" 
                        class="mt-1 block w-full rounded border border-gray-300 p-2 focus:border-indigo-500 focus:ring-indigo-500"
                        required
                    />
                </div>
                
                <div>
                    <label class="block text-sm font-medium text-gray-700">비밀번호</label>
                    <input 
                        v-model="password" 
                        type="password" 
                        class="mt-1 block w-full rounded border border-gray-300 p-2 focus:border-indigo-500 focus:ring-indigo-500"
                        required
                    />
                </div>

                <div v-if="errorMsg" class="text-sm text-red-600">
                    {{ errorMsg }}
                </div>

                <button 
                    type="submit" 
                    class="w-full rounded bg-indigo-600 px-4 py-2 font-bold text-white hover:bg-indigo-700 font-bold transition"
                >
                    로그인
                </button>
            </form>
            
            <div class="mt-4 flex justify-between text-sm text-gray-600">
                <button @click="showResetModal = true" class="hover:underline">비밀번호 찾기</button>
                <p>
                    계정이 없으신가요? <router-link to="/signup" class="text-indigo-600 hover:underline">회원가입</router-link>
                </p>
            </div>
        </div>

        <!-- 비밀번호 찾기 모달 -->
        <div v-if="showResetModal" class="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50">
            <div class="w-full max-w-sm rounded-lg bg-white p-6 shadow-lg">
                <h3 class="mb-4 text-lg font-bold text-gray-800">비밀번호 재설정</h3>
                <p class="mb-4 text-xs text-gray-500">가입하신 아이디와 이름을 입력하시면 비밀번호를 재설정할 수 있습니다.</p>
                
                <form @submit.prevent="handleResetPassword" class="space-y-3">
                    <input 
                        v-model="resetForm.username" 
                        placeholder="아이디" 
                        class="w-full rounded border p-2"
                        required
                    />
                    <input 
                        v-model="resetForm.first_name" 
                        placeholder="이름 (실명)" 
                        class="w-full rounded border p-2"
                        required
                    />
                    <input 
                        v-model="resetForm.new_password" 
                        type="password" 
                        placeholder="새 비밀번호" 
                        class="w-full rounded border p-2"
                        required
                    />
                    
                    <div v-if="resetMsg" :class="resetSuccess ? 'text-blue-600' : 'text-red-600'" class="text-xs">
                        {{ resetMsg }}
                    </div>

                    <div class="flex justify-end gap-2 mt-4">
                        <button type="button" @click="showResetModal = false" class="rounded bg-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-400">취소</button>
                        <button type="submit" class="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">변경하기</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</template>
