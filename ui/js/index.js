// 全局变量和状态
var currentWord = '';

// API 调用函数
function checkAnswer(answer) {
    api.checkAnswer(answer)
        .then(function(result) {
            const {similarity, passed, correct_meaning} = result;
            if(!passed){
                addToWrongList(currentWord);
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
    // TODO: 实现错词本更新逻辑
}

// 页面加载完成后的初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    getNextWord(); // 获取第一个单词
    // 更新播放按钮点击事件
    document.getElementById('play-audio').onclick = function() {
        playWordAudio(currentWord);
    };
});