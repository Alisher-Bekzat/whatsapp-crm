// ============= API Calls =============

async function fetchColumns() {
    const res = await fetch('/api/columns');
    return await res.json();
}

async function fetchTasks() {
    const res = await fetch('/api/tasks');
    return await res.json();
}

async function createTask(title, author, columnId) {
    const res = await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, author, column_id: columnId })
    });
    return await res.json();
}

async function updateTaskColumn(taskId, columnId) {
    const res = await fetch(`/api/tasks/${taskId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ column_id: columnId })
    });
    return await res.json();
}

async function deleteTask(taskId) {
    const res = await fetch(`/api/tasks/${taskId}`, {
        method: 'DELETE'
    });
    return await res.json();
}

async function createColumn(name) {
    const res = await fetch('/api/columns', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
    });
    return await res.json();
}

async function renameColumn(colId, newName) {
    const res = await fetch(`/api/columns/${colId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName })
    });
    return await res.json();
}

async function deleteColumn(colId) {
    const res = await fetch(`/api/columns/${colId}`, {
        method: 'DELETE'
    });
    return await res.json();
}

async function startParser() {
    const res = await fetch('/api/parser/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ group_name: 'Group' })
    });
    return await res.json();
}

async function stopParser() {
    const res = await fetch('/api/parser/stop', {
        method: 'POST'
    });
    return await res.json();
}

async function getParserStatus() {
    const res = await fetch('/api/parser/status');
    return await res.json();
}

// ============= State =============

let allTasks = [];
let allColumns = [];
let currentColumnIdForTask = null;
let currentEditingColumnId = null;
let isParserRunning = false;

// ============= UI Rendering =============

async function renderBoard() {
    const board = document.getElementById('kanbanBoard');
    board.innerHTML = '';

    allColumns.forEach(column => {
        const columnTasks = allTasks.filter(t => t.column_id === column.id);
        const columnEl = createColumnElement(column, columnTasks);
        board.appendChild(columnEl);
    });
}

function createColumnElement(column, tasks) {
    const columnDiv = document.createElement('div');
    columnDiv.className = 'column';
    columnDiv.id = `column-${column.id}`;

    // Header
    const header = document.createElement('div');
    header.className = 'column-header';
    header.innerHTML = `
        <span class="column-title">${column.name}</span>
        <div class="column-actions">
            <button class="btn-icon" onclick="editColumn('${column.id}', '${column.name}')">✏️</button>
            <button class="btn-icon" onclick="deleteColumnHandler('${column.id}')">🗑️</button>
        </div>
    `;

    // Content
    const content = document.createElement('div');
    content.className = 'column-content';
    content.ondrop = (e) => handleDrop(e, column.id);
    content.ondragover = (e) => {
        e.preventDefault();
        content.classList.add('drag-over');
    };
    content.ondragleave = () => content.classList.remove('drag-over');

    // Tasks
    tasks.forEach(task => {
        const taskEl = createTaskElement(task);
        content.appendChild(taskEl);
    });

    // Add task button
    const addBtn = document.createElement('button');
    addBtn.className = 'add-task-btn';
    addBtn.textContent = '➕ Добавить задачу';
    addBtn.onclick = () => openAddTaskModal(column.id);
    content.appendChild(addBtn);

    columnDiv.appendChild(header);
    columnDiv.appendChild(content);

    return columnDiv;
}

function createTaskElement(task) {
    const taskDiv = document.createElement('div');
    taskDiv.className = 'task';
    taskDiv.draggable = true;
    taskDiv.id = `task-${task.id}`;

    taskDiv.ondragstart = (e) => {
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('taskId', task.id);
        taskDiv.classList.add('dragging');
    };

    taskDiv.ondragend = () => {
        taskDiv.classList.remove('dragging');
        document.querySelectorAll('.column-content').forEach(c => c.classList.remove('drag-over'));
    };

    taskDiv.innerHTML = `
        <div class="task-title">${task.title}</div>
        <div class="task-author">👤 ${task.author || 'Неизвестно'}</div>
        <div class="task-actions">
            <button class="btn btn-danger" onclick="deleteTaskHandler(${task.id})">🗑️ Удалить</button>
        </div>
    `;

    return taskDiv;
}

// ============= Drag & Drop =============

function handleDrop(e, columnId) {
    e.preventDefault();
    const taskId = parseInt(e.dataTransfer.getData('taskId'));
    
    updateTaskColumn(taskId, columnId).then(() => {
        loadBoard();
    });

    document.querySelectorAll('.column-content').forEach(c => c.classList.remove('drag-over'));
}

// ============= Modals =============

function openAddColumnModal() {
    document.getElementById('addColumnModal').classList.remove('hidden');
    document.getElementById('columnNameInput').focus();
}

function closeAddColumnModal() {
    document.getElementById('addColumnModal').classList.add('hidden');
}

function openAddTaskModal(columnId) {
    currentColumnIdForTask = columnId;
    document.getElementById('addTaskModal').classList.remove('hidden');
    document.getElementById('taskTitleInput').focus();
}

function closeAddTaskModal() {
    document.getElementById('addTaskModal').classList.add('hidden');
    currentColumnIdForTask = null;
}

function openEditColumnModal(colId, currentName) {
    currentEditingColumnId = colId;
    document.getElementById('editColumnNameInput').value = currentName;
    document.getElementById('editColumnModal').classList.remove('hidden');
    document.getElementById('editColumnNameInput').focus();
}

function closeEditColumnModal() {
    document.getElementById('editColumnModal').classList.add('hidden');
    currentEditingColumnId = null;
}

// ============= Event Handlers =============

document.getElementById('addColumnBtn').addEventListener('click', openAddColumnModal);
document.getElementById('confirmColumnBtn').addEventListener('click', async () => {
    const name = document.getElementById('columnNameInput').value.trim();
    if (name) {
        await createColumn(name);
        await loadBoard();
        closeAddColumnModal();
    }
});
document.getElementById('cancelColumnBtn').addEventListener('click', closeAddColumnModal);

document.getElementById('confirmTaskBtn').addEventListener('click', async () => {
    const title = document.getElementById('taskTitleInput').value.trim();
    const author = document.getElementById('taskAuthorInput').value.trim();
    if (title && currentColumnIdForTask) {
        await createTask(title, author, currentColumnIdForTask);
        await loadBoard();
        closeAddTaskModal();
    }
});
document.getElementById('cancelTaskBtn').addEventListener('click', closeAddTaskModal);

document.getElementById('confirmEditBtn').addEventListener('click', async () => {
    const newName = document.getElementById('editColumnNameInput').value.trim();
    if (newName && currentEditingColumnId) {
        await renameColumn(currentEditingColumnId, newName);
        await loadBoard();
        closeEditColumnModal();
    }
});
document.getElementById('cancelEditBtn').addEventListener('click', closeEditColumnModal);

// Parser button
document.getElementById('parserBtn').addEventListener('click', async () => {
    if (isParserRunning) {
        await stopParser();
        isParserRunning = false;
        document.getElementById('parserBtn').textContent = '▶️ Запустить парсер';
        document.getElementById('statusText').textContent = 'Статус: Остановлен';
    } else {
        await startParser();
        isParserRunning = true;
        document.getElementById('parserBtn').textContent = '⏸️ Остановить парсер';
        document.getElementById('statusText').textContent = 'Статус: Работает 🟢';
    }
});

// Global functions for onclick handlers
window.editColumn = (colId, currentName) => {
    openEditColumnModal(colId, currentName);
};

window.deleteColumnHandler = async (colId) => {
    if (confirm('Удалить колонку? Задачи переместятся в первую колонку.')) {
        await deleteColumn(colId);
        await loadBoard();
    }
};

window.deleteTaskHandler = async (taskId) => {
    if (confirm('Удалить задачу?')) {
        await deleteTask(taskId);
        await loadBoard();
    }
};

// ============= Init =============

async function loadBoard() {
    allColumns = await fetchColumns();
    allTasks = await fetchTasks();
    
    // Добавить задачи в колонки
    allColumns.forEach(col => {
        col.tasks = allTasks.filter(t => t.column_id === col.id);
    });

    await renderBoard();
}

async function checkParserStatus() {
    const status = await getParserStatus();
    isParserRunning = status.is_running;
    
    if (isParserRunning) {
        document.getElementById('parserBtn').textContent = '⏸️ Остановить парсер';
        document.getElementById('statusText').textContent = 'Статус: Работает 🟢';
    } else {
        document.getElementById('parserBtn').textContent = '▶️ Запустить парсер';
        document.getElementById('statusText').textContent = 'Статус: Остановлен';
    }
}

// Close modals on Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeAddColumnModal();
        closeAddTaskModal();
        closeEditColumnModal();
    }
});

// Close modals on outside click
document.querySelectorAll('.modal').forEach(modal => {
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.add('hidden');
        }
    });
});

// Load board on startup
window.addEventListener('load', async () => {
    await loadBoard();
    await checkParserStatus();
    
    // Refresh every 5 seconds
    setInterval(loadBoard, 5000);
});
