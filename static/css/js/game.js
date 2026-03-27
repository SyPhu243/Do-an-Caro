function initBoard(size, room){
    const boardEl = document.getElementById('board');
    if(!boardEl) return;
    boardEl.innerHTML = '';
    for(let r=0;r<size;r++){
        for(let c=0;c<size;c++){
            const cell = document.createElement('div');
            cell.className = 'cell';
            cell.dataset.r = r; cell.dataset.c = c;
            cell.addEventListener('click', ()=>{
                alert('Click: ' + r + ',' + c + ' (room ' + room + ')');
            });
            boardEl.appendChild(cell);
        }
    }
}