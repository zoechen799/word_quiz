document.addEventListener('DOMContentLoaded', function() {
    // 添加点击动画效果
    const tiles = document.querySelectorAll('.metro-tile');
    
    tiles.forEach(tile => {
        tile.addEventListener('click', function(e) {
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = 'translateY(-5px)';
            }, 200);
        });
    });
});
