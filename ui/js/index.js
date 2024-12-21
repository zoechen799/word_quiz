// 全局变量和状态
var currentWord = '';
var currentWrongCounts = {};
let currentWrongWordsPage = 1;
const wrongWordsPerPage = 5;

// API 调用函数
function checkAnswer(answer) {
    if(currentWrongCounts[currentWord] !== undefined){
        currentWrongCounts[currentWord]++;
    }else{
        currentWrongCounts[currentWord] = 0;
    }
    api.checkAnswer(answer)
        .then(function(result) {
            const {similarity, passed, correct_meaning, wrong_count} = result;
            var wrongCount = Math.max(currentWrongCounts[currentWord], wrong_count? wrong_count : 0);
            if( !passed && wrongCount < 3 ) {
                if (similarity >= 50) {
                    showToast("已经接近了，加油！", "warning");
                } else {
                    showToast("再想想", "error");
                }
                if(wrong_count > 1) {
                    addToWrongList(currentWord);
                }
            }else{
                showResultDialog(result);
            }
            return result.passed;
        })
        .catch(function(error) {
            console.error('Error checking answer:', error);
            alert('检查答案失败：' + error.message);
        });
}

function addToWrongList() {
    api.addToWrongList(currentWord)
        .then(function() {
            updateWrongWordsList();
        })
        .catch(function(error) {
            console.error('Error adding to wrong list:', error);
            alert('添加到错词本失败：' + error.message);
        });
}

// 添加播放音频函数
function playWordAudio(word) {
    var audio = new Audio('/api/word-audio/' + word);
    audio.play().catch(function(error) {
        console.error('播放失败:', error);
    });
}

function getCurrentWord() {
    api.getCurrentWord()
        .then(function(data) {
            currentWord = data.word;
            document.getElementById('word-label').textContent = data.word;
            document.getElementById('phonetic').textContent = data.phonetic || '';
            document.getElementById('part-of-speech').textContent = data.part_of_speech || '';
            document.getElementById('answer-input').value = '';
            hideResultDialog();
            playWordAudio(currentWord);
        })
        .catch(function(error) {
            console.error('Error getting next word:', error);
            alert('获取当前单词失败：' + error.message);
        });
}

function getNextWord() {
    api.getNextWord()
        .then(function(data) {
            currentWord = data.word;
            document.getElementById('word-label').textContent = data.word;
            document.getElementById('phonetic').textContent = data.phonetic || '';
            document.getElementById('part-of-speech').textContent = data.part_of_speech || '';
            document.getElementById('answer-input').value = '';
            hideResultDialog();
            playWordAudio(currentWord);
            updateProgress();
        })
        .catch(function(error) {
            console.error('Error getting next word:', error);
            alert('获取下一个单词失败：' + error.message);
        });
}

// UI 处理函数
function showResultDialog(result) {
    var dialog = document.getElementById('result-dialog');
    var dialogTitle = document.getElementById('dialog-title');
    var correctAnswer = document.getElementById('correct-answer');
    
    dialogTitle.textContent = result.passed ? "恭喜正确！" : "回答错误";
    correctAnswer.textContent = "正确答案：" + result.correct_meaning;
    dialog.style.display = 'block';
}

function hideResultDialog() {
    document.getElementById('result-dialog').style.display = 'none';
}

// 事件处理函数
function handleAnswer() {
    var answerInput = document.getElementById('answer-input');
    var answer = answerInput.value.trim();
    if (answer) {
        checkAnswer(answer);
    }
}

// 初始化事件监听
function initializeEventListeners() {
    // Next按钮点击事件
    document.getElementById('next-button').addEventListener('click', handleAnswer);
    
    // 输入框回车事件
    document.getElementById('answer-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            handleAnswer();
        }
    });
    
    // 对话框中的"下一题"按钮
    document.getElementById('next-word-btn').addEventListener('click', getNextWord);
    
    // 对话框中的"加入错词本"按钮
    document.getElementById('add-wrong-list-btn').addEventListener('click', function() {
        addToWrongList();
        getNextWord();
    });
}

// 更新错词本列表显示
function updateWrongWordsList() {
    api.getWrongList(currentWrongWordsPage, wrongWordsPerPage)
        .then(data => {
            const wrongWordsPanel = document.querySelector('.wrong-words-panel');
            const listContainer = wrongWordsPanel.querySelector('.wrong-words-list');
            const paginationContainer = wrongWordsPanel.querySelector('.pagination');
            
            // 清空现有内容
            listContainer.innerHTML = '';
            
            // 如果没有错词，显示提示信息
            if (data.total_words === 0) {
                listContainer.innerHTML = '<div class="empty-message">还没有错词记录</div>';
                paginationContainer.style.display = 'none';
                return;
            }
            
            // 显示错词列表
            data.words.forEach(word => {
                const wordItem = document.createElement('div');
                wordItem.className = 'wrong-word-item';
                wordItem.innerHTML = `
                    <div class="word-info">
                        <span class="word">${word.word}</span>
                        <span class="meaning">${word.meaning}</span>
                    </div>
                    <span class="wrong-count">错误: ${word.error_count}次</span>
                `;
                listContainer.appendChild(wordItem);
            });
            
            // 更新分页控件
            paginationContainer.style.display = 'flex';
            updatePagination(data.total_pages);
        })
        .catch(error => {
            console.error('获取错词列表失败:', error);
        });
}

function updatePagination(totalPages) {
    const paginationContainer = document.querySelector('.wrong-words-panel .pagination');
    paginationContainer.innerHTML = '';
    
    // 上一页按钮
    const prevButton = document.createElement('button');
    prevButton.className = 'pagination-btn';
    prevButton.textContent = '上一页';
    prevButton.disabled = currentWrongWordsPage === 1;
    prevButton.onclick = () => {
        if (currentWrongWordsPage > 1) {
            currentWrongWordsPage--;
            updateWrongWordsList();
        }
    };
    
    // 页码显示
    const pageInfo = document.createElement('span');
    pageInfo.className = 'page-info';
    pageInfo.textContent = `${currentWrongWordsPage} / ${totalPages}`;
    
    // 下一页按钮
    const nextButton = document.createElement('button');
    nextButton.className = 'pagination-btn';
    nextButton.textContent = '下一页';
    nextButton.disabled = currentWrongWordsPage === totalPages;
    nextButton.onclick = () => {
        if (currentWrongWordsPage < totalPages) {
            currentWrongWordsPage++;
            updateWrongWordsList();
        }
    };
    
    paginationContainer.appendChild(prevButton);
    paginationContainer.appendChild(pageInfo);
    paginationContainer.appendChild(nextButton);
}

function showToast(message, type) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = 'toast ' + (type === 'warning' ? 'toast-warning' : 'toast-error');
    toast.style.display = 'flex';
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => {
            toast.style.display = 'none';
            toast.style.opacity = '0.6';
        }, 300);
    }, 1000);
}

/**
 * 更新学习进度显示
 */
function updateProgress() {
    api.getProgress()
        .then(result => {
            const {current_chapter_index, current_index,current_chapter_progress,
                current_chapter_total_words, chapter_current,
                progress_percentage
            } = result;
            
            const chapterSelect = document.getElementById('chapter-select');
            chapterSelect.value = current_chapter_index + 1;

            // 更新总进度
            const progressBar = document.querySelector('.progress-bar');
            const progressText = document.querySelector('.progress-text');
            
            progressBar.style.width = `${current_chapter_progress}%`;
            progressText.textContent = `${chapter_current} / ${current_chapter_total_words}`;
            
            const chapterInfo = document.querySelector('.chapter-info');
            chapterInfo.textContent = `第${current_chapter_index + 1}章`;
        })
        .catch(error => {
            console.error('获取进度失败:', error);
        });
}

function initChapterSelect() {
    const chapterSelect = document.getElementById('chapter-select');
    // 生成33个章节的选项
    for (let i = 1; i <= 33; i++) {
        const option = document.createElement('option');
        option.value = i;
        option.textContent = `第${i}章`;
        chapterSelect.appendChild(option);
    }

    updateProgress();
    
    // 监听选择变化
    chapterSelect.addEventListener('change', function() {
        const selectedChapter = parseInt(this.value);
        api.switchChapter(selectedChapter-1)
            .then(() => {
                // 切换成功后刷新单词和进度
                updateProgress();
                getCurrentWord();
            })
            .catch(error => {
                console.error('切换章节失败:', error);
            });
    });
}

// 页面加载完成后的初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    getCurrentWord(); // 获取第一个单词
    // 更新播放按钮点击事件
    document.getElementById('play-audio').onclick = function() {
        playWordAudio(currentWord);
    };
    updateWrongWordsList();
    initChapterSelect();

    // 头像菜单相关
    const avatarBtn = document.getElementById('avatar-btn');
    const avatarMenu = document.getElementById('avatar-menu');
    const settingsBtn = document.getElementById('settings-btn');
    const logoutBtn = document.getElementById('logout-btn');

    // 点击头像显示/隐藏菜单
    avatarBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        avatarMenu.classList.toggle('show');
    });

    // 点击页面其他地方关闭菜单
    document.addEventListener('click', () => {
        avatarMenu.classList.remove('show');
    });

    // 防止点击菜单内部时关闭菜单
    avatarMenu.addEventListener('click', (e) => {
        e.stopPropagation();
    });

    // 设置按钮点击事件
    settingsBtn.addEventListener('click', () => {
        // TODO: 实现设置功能或跳转到设置页面
        window.location.href = '/settings.html';
    });

    // 退出按钮点击事件
    logoutBtn.addEventListener('click', async () => {
        try {
            localStorage.removeItem('token');
            // 退出成功后跳转到登录页
            window.location.href = '/login.html';
        } catch (error) {
            console.error('退出失败:', error);
            showToast('退出失败，请重试');
        }
    });
});