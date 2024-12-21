// 定义API基础URL
const BASE_URL = '';

// 获取认证头
function getAuthHeader() {
    var token = localStorage.getItem('token');
    return token ? {'Authorization': 'Bearer ' + token} : {};
}

// HTTP 状态码处理
function handleResponse(response) {
    if (response.status === 401) {
        // 未授权，跳转到登录页面
        window.location.href = '/login.html';
        return Promise.reject(new Error('Unauthorized'));
    }
    
    if (!response.ok) {
        return response.json()
            .catch(() => ({}))
            .then(function(error) {
                throw new Error(error.detail || 'HTTP error! status: ' + response.status);
            });
    }
    
    return response.json();
}

// 统一的请求处理函数
function request(url, options = {}) {
    var defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            ...getAuthHeader()  // 添加认证头
        },
        credentials: 'include', // 包含 cookies
    };

    return fetch(BASE_URL + url, {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers,
        },
    })
    .then(handleResponse)
    .catch(function(error) {
        console.error('API request failed:', error);
        throw error;
    });
}

// API 接口封装
var api = {
    // 登录
    login: function(username, password) {
        var token = btoa(username + ':' + password);
        return request('/api/login', {
            method: 'POST',
            headers: {
                'Authorization': 'Basic ' + token
            }
        }).then(function(response) {
            // 登录成功后保存token
            localStorage.setItem('token', token);
            return response;
        });
    },

    // 登出
    logout: function() {
        localStorage.removeItem('token');
        window.location.href = '/login.html';
    },

    // 检查答案
    checkAnswer: function(answer) {
        return request('/api/check-answer', {
            method: 'POST',
            body: JSON.stringify({ answer })
        });
    },
    // 获取当前单词
    getCurrentWord: function() {
        return request('/api/current-word', {
            method: 'GET'
        });
    },

    // 获取下一个单词
    getNextWord: function() {
        return request('/api/next-word', {
            method: 'POST'
        });
    },

    // 添加到错词本
    addToWrongList: function(word) {
        return request('/api/add-to-wrong-list', {
            method: 'POST',
            body: JSON.stringify({ word })
        });
    },

    // 获取错词本列表
    getWrongList: function(page, pageSize) {
        return request('/api/get-wrong-list', {
            method: 'GET',
            params: { 
                page: page || 1, 
                per_page: pageSize || 5 
            }
        });
    },

    // 开始错词复习
    startWrongWordsReview: function() {
        return request('/api/start-wrong-words-review', {
            method: 'POST'
        });
    },

    // 切换章节
    switchChapter: function(index) {
        return request('/api/switch-chapter', {
            method: 'POST',
            body: JSON.stringify({ index })
        });
    },

    // 获取进度
    getProgress: function() {
        return request('/api/progress', {
            method: 'GET'
        });
    },
};

// 导出 api 对象
window.api = api; 