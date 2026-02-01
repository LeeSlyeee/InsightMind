<script setup>
import { ref, computed, onMounted } from 'vue';
import api from '@/api';
import axios from 'axios'; 
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale,
  ArcElement,
  PointElement,
  LineElement,
  Filler
} from 'chart.js'
import { Bar, Doughnut, Line } from 'vue-chartjs'

// Register ChartJS components
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement, PointElement, LineElement, Filler)

const allDiaries = ref([]);
const highRiskDiaries = ref([]); 
const patients = ref([]);
const totalPatients = ref(0);
const totalDiaryCount = ref(0); 
const debugLog = ref("초기화 중...");
const loading = ref(false); // 누락된 변수 복구
const generatedCode = ref(null); // 누락된 변수 복구
const errorMsg = ref(''); // 누락된 변수 복구

// Chart Data Computed Properties
const flowChartData = computed(() => {
    if (!allDiaries.value || allDiaries.value.length === 0) {
        return { labels: [], datasets: [] };
    }

    // 1. 오늘 날짜 기준 (접속일)
    const today = new Date();
    
    // 2. 오늘로부터 과거 7일 날짜 생성
    const chartLabels = [];
    const chartData = [];

    for (let i = 6; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(d.getDate() - i);
        const dateStr = d.toISOString().split('T')[0];
        
        // 라벨 (MM/DD)
        chartLabels.push(dateStr.slice(5).replace('-', '/'));

        // 해당 날짜의 평균 점수 계산 (한국 시간 보정 없이 단순 문자열 매칭 시 오차 가능성 있으나, ISO 포맷 기준 일치)
        // 실제 운영 시 timezone 고려 필요할 수 있음.
        const targetDiaries = allDiaries.value.filter(item => item.created_at.startsWith(dateStr));
        if (targetDiaries.length > 0) {
            const sum = targetDiaries.reduce((acc, cur) => acc + (cur.mood_score || 0), 0);
            chartData.push(sum / targetDiaries.length);
        } else {
            chartData.push(null); // 데이터 끊김 표현
        }
    }

    return {
        labels: chartLabels,
        datasets: [{
            label: '일별 평균 기분',
            data: chartData,
            borderColor: '#4F46E5',
            backgroundColor: 'rgba(79, 70, 229, 0.1)',
            tension: 0.4,
            fill: true,
            spanGaps: true 
        }]
    };
});

const riskDistributionData = computed(() => {
    if (!allDiaries.value || !Array.isArray(allDiaries.value)) {
        return {
            labels: ['안정', '주의', '위험'],
            datasets: [{ data: [0, 0, 0], backgroundColor: ['#10B981', '#FBBF24', '#EF4444'], borderWidth: 0 }]
        };
    }

    // 전체 일기 기준 분포 (mood_score 없을 경우 대비)
    const dangerous = allDiaries.value.filter(d => (d.mood_score || 0) <= 2).length;
    const caution = allDiaries.value.filter(d => (d.mood_score || 0) === 3 || (d.mood_score || 0) === 4).length;
    const stable = allDiaries.value.filter(d => (d.mood_score || 0) >= 5).length;
    
    return {
        labels: ['안정', '주의', '위험'],
        datasets: [{
            data: [stable, caution, dangerous],
            backgroundColor: ['#10B981', '#FBBF24', '#EF4444'],
            borderWidth: 0
        }]
    };
});

// 차트 옵션 유지
const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
        y: { beginAtZero: true, max: 10, grid: { color: '#f3f4f6' } }, // 점수 10점 만점
        x: { grid: { display: false } }
    }
};

const doughnutOptions = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '70%',
    plugins: { legend: { position: 'bottom' } }
};

// Data Fetching
// Data Fetching
// Data Fetching
const fetchDashboardData = async () => {
    loading.value = true;
    debugLog.value = "데이터 로딩 시작...";

    
    try {
        const baseURL = import.meta.env.PROD ? '/api/v1/' : 'http://127.0.0.1:8000/api/v1/';
        debugLog.value += `\nBaseURL: ${baseURL}`;

        // 1. 환자 목록 호출
        debugLog.value += "\n1. 환자 목록 호출 중...";
        const resPatients = await axios.get(baseURL + 'diaries/staff/patients/');
        debugLog.value += `\n   - 성공: ${resPatients.data.length}명 수신`;
        
        patients.value = resPatients.data || [];
        totalPatients.value = patients.value.length;

        // 2. 일기 목록 호출
        debugLog.value += "\n2. 일기 목록 호출 중...";
        const resDiaries = await axios.get(baseURL + 'diaries/staff/diaries/');
        
        // 데이터 구조 파악
        const rawData = resDiaries.data.results || resDiaries.data;
        debugLog.value += `\n   - 성공: ${Array.isArray(rawData) ? rawData.length : '배열아님'}건 수신`;

        allDiaries.value = Array.isArray(rawData) ? rawData : [];
        allDiaries.value = allDiaries.value.filter(d => d && d.created_at);

        // 고위험군
        highRiskDiaries.value = allDiaries.value
            .filter(d => (d.mood_score || 0) <= 2)
            .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
            .slice(0, 10);

        totalDiaryCount.value = allDiaries.value.length;
        debugLog.value += "\n✅ 모든 데이터 처리 완료";

    } catch (err) {
        console.error("대시보드 에러:", err);
        debugLog.value += `\n❌ 에러 발생: ${err.message}`;
        if (err.response) {
            debugLog.value += `\n   - Status: ${err.response.status}`;
            debugLog.value += `\n   - Data: ${JSON.stringify(err.response.data).slice(0, 50)}...`;
        }
        
        // 에러 발생 시 빈값 처리
        allDiaries.value = [];
        highRiskDiaries.value = [];
    } finally {
        loading.value = false;
    }
};

const generateCode = async () => {
    /* 토큰 없는 직접 호출로 변경 */
    loading.value = true;
    errorMsg.value = '';
    generatedCode.value = null;
    try {
        const baseURL = import.meta.env.PROD ? '/api/v1/' : 'http://127.0.0.1:8000/api/v1/';
        const response = await axios.post(baseURL + 'centers/generate/');
        generatedCode.value = response.data.code;
        
        // [UX] 생성 즉시 클립보드 복사
        copyToClipboard();
        
    } catch (err) {
        console.error(err);
        errorMsg.value = '코드 생성 실패: ' + (err.response?.data?.error || '알 수 없는 오류');
    } finally {
        loading.value = false;
    }
};

/* 기존 헬퍼 함수 유지 */
/* 강력한 클립보드 복사 (HTTP 지원) */
const copyToClipboard = () => {
    if (!generatedCode.value) return;
    const text = generatedCode.value;

    // 1. 최신 브라우저 & HTTPS 환경
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text)
            .then(() => alert('인증 코드가 복사되었습니다.'))
            .catch(() => fallbackCopy(text));
    } else {
        // 2. HTTP 환경 (Fallback)
        fallbackCopy(text);
    }
};

const fallbackCopy = (text) => {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    
    // 화면 튀는 현상 방지
    textArea.style.top = "0";
    textArea.style.left = "0";
    textArea.style.position = "fixed";
    textArea.style.opacity = "0"; 
    
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
        const successful = document.execCommand('copy');
        if (successful) {
            alert('인증 코드가 복사되었습니다.');
        } else {
            prompt("자동 복사에 실패했습니다. 아래 코드를 직접 복사해주세요:", text);
        }
    } catch (err) {
        prompt("자동 복사에 실패했습니다. 아래 코드를 직접 복사해주세요:", text);
    }
    
    document.body.removeChild(textArea);
};

const formatDate = (dateString) => {
    if (!dateString) return '-';
    // OCI 마이그레이션 데이터의 시간대가 UTC일 수 있으므로 로컬 시간으로 변환
    const date = new Date(dateString);
    return date.toLocaleString(); // 날짜+시간 표시
};

let intervalId = null;

onMounted(() => {
    fetchDashboardData();
    // 5초마다 데이터 갱신 (실시간성 확보)
    intervalId = setInterval(fetchDashboardData, 5000);
});

import { onUnmounted } from 'vue';
onUnmounted(() => {
    if (intervalId) clearInterval(intervalId);
});
</script>

<template>
    <div class="min-h-screen bg-slate-50 p-6 font-sans">
        <header class="mb-10 flex items-center justify-between">
            <div>
                <h1 class="text-4xl font-extrabold text-slate-900 tracking-tight">InsightMind Dashboard</h1>
                <p class="text-xl text-slate-500 font-medium mt-2">도봉구 정신건강복지센터 통합 관제 시스템</p>
            </div>
            <div class="flex items-center gap-6">
                <button 
                  @click="$router.push('/admin/patients')"
                  class="bg-white border border-slate-300 text-slate-700 font-bold py-3 px-6 rounded-xl hover:bg-slate-50 transition flex items-center gap-3 text-lg"
                >
                    <span>👥 전체 환자 관리</span>
                </button>
                <div class="bg-white px-6 py-3 rounded-xl shadow-sm border border-slate-200 text-base">
                    <span class="text-slate-500">담당자:</span>
                    <span class="font-bold text-slate-800 ml-2 text-lg">관리자(Admin)</span>
                </div>
            </div>
        </header>

        <!-- 상단 통계 카드 -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-8 mb-10">
            <div class="bg-white p-8 rounded-3xl shadow-sm border border-slate-100 flex flex-col justify-between">
                <div>
                    <p class="text-lg font-bold text-slate-500 mb-2">총 등록 대상자</p>
                    <h3 class="text-5xl font-extrabold text-slate-800">{{ totalPatients }}<span class="text-xl font-normal text-slate-400 ml-2">명</span></h3>
                </div>
                <div class="mt-6 flex items-center text-sm font-medium text-green-600 bg-green-50 w-fit px-3 py-1.5 rounded-lg">
                    <span>실시간 업데이트됨</span>
                </div>
            </div>
            <div class="bg-white p-8 rounded-3xl shadow-sm border border-slate-100 flex flex-col justify-between">
                <div>
                    <p class="text-lg font-bold text-slate-500 mb-2">고위험군 집중 관리</p>
                    <h3 class="text-5xl font-extrabold text-red-600">{{ highRiskDiaries.length }}<span class="text-xl font-normal text-slate-400 ml-2">건</span></h3>
                </div>
                <div class="mt-6 flex items-center text-sm font-medium text-red-600 bg-red-50 w-fit px-3 py-1.5 rounded-lg">
                    <span>⚠️ 최근 감지 (10건)</span>
                </div>
            </div>
             <div class="bg-white p-8 rounded-3xl shadow-sm border border-slate-100 flex flex-col justify-between">
                <div>
                    <p class="text-lg font-bold text-slate-500 mb-2">누적 일기 데이터</p>
                    <h3 class="text-5xl font-extrabold text-blue-600">{{ totalDiaryCount }}<span class="text-xl font-normal text-slate-400 ml-2">건</span></h3>
                </div>
                <div class="mt-6 flex items-center text-sm font-medium text-slate-500">
                    <span>전체 기간 합계</span>
                </div>
            </div>
             <div class="bg-white p-8 rounded-3xl shadow-sm border border-slate-100 flex flex-col justify-between bg-gradient-to-br from-indigo-500 to-purple-600 text-white">
                <div>
                    <p class="text-lg font-bold text-indigo-100 mb-2">신규 연동 코드 발급</p>
                     <button 
                        @click="generateCode"
                        class="mt-4 w-full bg-white/20 hover:bg-white/30 text-white font-bold py-3 px-6 rounded-xl transition text-base flex items-center justify-center gap-2"
                     >
                        <span>🔑 코드 생성하기</span>
                     </button>
                </div>
                 <div v-if="generatedCode" class="mt-4 bg-white text-indigo-900 p-3 rounded-xl text-center relative group cursor-pointer" @click="copyToClipboard">
                    <span class="font-mono font-bold tracking-wider text-2xl">{{ generatedCode }}</span>
                    <div class="absolute inset-0 bg-black/10 opacity-0 group-hover:opacity-100 flex items-center justify-center rounded-xl transition">
                        <span class="text-xs font-bold">복사하기</span>
                    </div>
                 </div>
            </div>
        </div>

        <!-- 메인 차트 영역 -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-10">
            <!-- 1. 주간 기분 흐름 -->
            <div class="col-span-2 bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
                <h3 class="text-2xl font-bold text-slate-800 mb-8">📉 전체 대상자 평균 기분 변화 (주간)</h3>
                <div class="h-80">
                    <Line :data="flowChartData" :options="commonOptions" />
                </div>
            </div>
            
            <!-- 2. 위험군 분포 -->
            <div class="bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
                <h3 class="text-2xl font-bold text-slate-800 mb-8">🚨 감정 상태 분포 (전체)</h3>
                <div class="h-64 relative" v-if="riskDistributionData?.datasets?.[0]?.data">
                    <Doughnut :data="riskDistributionData" :options="doughnutOptions" />
                </div>
                 <div class="mt-8 space-y-4" v-if="riskDistributionData?.datasets?.[0]?.data">
                    <!-- 범례 -->
                    <div class="flex justify-between text-base">
                        <span class="flex items-center"><span class="w-3 h-3 rounded-full bg-green-500 mr-3"></span>안정 (5점 이상)</span>
                        <span class="font-bold text-slate-700 text-lg">{{ riskDistributionData.datasets[0].data[0] || 0 }}건</span>
                    </div>
                    <div class="flex justify-between text-base">
                        <span class="flex items-center"><span class="w-3 h-3 rounded-full bg-yellow-400 mr-3"></span>주의 (3-4점)</span>
                        <span class="font-bold text-slate-700 text-lg">{{ riskDistributionData.datasets[0].data[1] || 0 }}건</span>
                    </div>
                     <div class="flex justify-between text-base">
                        <span class="flex items-center"><span class="w-3 h-3 rounded-full bg-red-500 mr-3"></span>위험 (2점 이하)</span>
                        <span class="font-bold text-red-600 text-lg">{{ riskDistributionData.datasets[0].data[2] || 0 }}건</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- 하단: 최근 알림 목록 -->
         <div class="bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
            <h3 class="text-2xl font-bold text-slate-800 mb-6">🔔 실시간 모니터링 알림</h3>
            <div class="overflow-x-auto">
                <table class="w-full text-base text-left text-slate-500">
                    <thead class="text-sm text-slate-700 uppercase bg-slate-50">
                        <tr>
                            <th class="px-8 py-5">시간</th>
                            <th class="px-8 py-5">대상자</th>
                            <th class="px-8 py-5">이벤트</th>
                            <th class="px-8 py-5">감정 점수</th>
                            <th class="px-8 py-5">상태</th>
                            <th class="px-8 py-5">조치</th>
                        </tr>
                    </thead>
                    <tbody>
                        <!-- 실제 데이터 렌더링 -->
                        <tr v-for="diary in highRiskDiaries" :key="diary.id" class="bg-white border-b hover:bg-slate-50 transition">
                            <td class="px-8 py-6 font-medium">{{ formatDate(diary.created_at) }}</td>
                            <td class="px-8 py-6 font-bold text-slate-900 text-lg">User_{{ diary.id }}</td>
                            <td class="px-8 py-6 text-red-600 hover:text-red-800 cursor-pointer font-medium" :title="diary.content || ''">
                                {{ (diary.content || '').length > 25 ? (diary.content || '').slice(0,25) + '...' : (diary.content || '-') }}
                            </td>
                            <td class="px-8 py-6">
                                <span class="font-extrabold text-xl" :class="diary.mood_score <= 2 ? 'text-red-500' : 'text-slate-700'">
                                    {{ diary.mood_score }}점
                                </span>
                            </td>
                            <td class="px-8 py-6">
                                <span v-if="diary.mood_score <= 2" class="bg-red-100 text-red-800 text-sm font-bold px-4 py-1.5 rounded-full">고위험</span>
                                <span v-else class="bg-orange-100 text-orange-800 text-sm font-bold px-4 py-1.5 rounded-full">주의</span>
                            </td>
                            <td class="px-8 py-6">
                                <button 
                                    @click="$router.push(`/admin/patients/${diary.user}`)"
                                    class="text-blue-600 hover:text-blue-900 font-bold text-lg border border-blue-200 bg-blue-50 px-4 py-2 rounded-lg hover:bg-blue-100 transition"
                                >
                                    상세보기
                                </button>
                            </td>
                        </tr>

                        <!-- 데이터가 없을 경우 -->
                        <tr v-if="highRiskDiaries.length === 0">
                            <td colspan="6" class="px-6 py-8 text-center text-slate-400">
                                현재 감지된 위험 징후 데이터가 없습니다.
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
         </div>
    </div>
</template>
