// 检查是否已登录
if (!localStorage.getItem('token')) {
    window.location.href = '/login.html';
}

let currentWord = '';
const token = localStorage.getItem('token');

function fetchWord() {
    fetch('/api/current-word', {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (response.status === 401) {
            window.location.href = '/login.html';
            return;
        }
        return response.json();
    })
    .then(data => {
        document.getElementById('word').textContent = data.word;
        document.getElementById('phonetic').textContent = data.phonetic || '';
        currentWord = data.word;
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

function checkAnswer(answer) {
    return fetch('/api/check-answer', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ answer })
    })
    .then(response => response.json())
    .catch(error => {
        console.error('Error:', error);
        return null;
    });
}

function nextWord() {
    return fetch('/api/next-word', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(() => fetchWord())
    .catch(error => {
        console.error('Error:', error);
    });
}

// 添加播放音频的函数
function playWordAudio(word) {
    const audio = new Audio(`/api/word-audio/${word}`);
    audio.play().catch(error => console.error('播放失败:', error));
}

document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('answer');
    const feedback = document.getElementById('feedback');

    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            checkAnswer(input.value)
                .then(result => {
                    if (result) {
                        if (result.similarity >= 60) {
                            feedback.textContent = '正确！';
                            feedback.className = 'feedback';
                            input.value = '';
                            return nextWord();
                        } else if (result.similarity >= 20) {
                            feedback.textContent = '已经接近了，请再想想。';
                            feedback.className = 'feedback yellow-feedback';
                        } else {
                            feedback.textContent = '不正确，请重新输入';
                            feedback.className = 'feedback red-feedback';
                            input.classList.add('shake');
                            setTimeout(() => {
                                input.classList.remove('shake');
                            }, 500);
                        }
                    }
                });
        }
    });

    // 初始加载单词
    fetchWord();

    // 更新播放按钮的事件监听
    document.getElementById('playButton').addEventListener('click', () => {
        if (currentWord) {
            playWordAudio(currentWord);
        }
    });

    // 保留单词点击播放功能
    document.getElementById('word').addEventListener('click', () => {
        if (currentWord) {
            playWordAudio(currentWord);
        }
    });
}); 