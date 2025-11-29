document.addEventListener('DOMContentLoaded', function() {
    const addButton = document.getElementById('add-blocks-btn');
    const container = document.getElementById('cases-container');
    const form = document.getElementById('test-form');
    let questionCounter = 1;
    
    // 1. Логика добавления новых блоков
    addButton.addEventListener('click', function() {
        questionCounter++;
        const newBlock = document.createElement('div');
        newBlock.className = 'small-block test-case'; // Добавили класс test-case для поиска
        newBlock.innerHTML = `
            <h4>Тест-кейс ${questionCounter}</h4>
            <div class="answer-options">
                <div class="answer-option">
                    <input type="text" class="param1" placeholder="Параметр 1">
                </div>
                <div class="answer-option">
                    <input type="text" class="param2" placeholder="Параметр 2">
                </div>
                <div class="answer-option">
                    <input type="text" class="result" placeholder="Результат">
                </div>
            </div>
        `;
        container.appendChild(newBlock);
    });
    
    // 2. Логика отправки формы (сбор массива)
    form.addEventListener('submit', function(e) {
        e.preventDefault(); // Останавливаем стандартную отправку
        
        const cases = document.querySelectorAll('.test-case');
        const dataArray = []; // Наш массив массивов
        
        let isValid = true;

        cases.forEach(block => {
            const p1 = block.querySelector('.param1').value.trim();
            const p2 = block.querySelector('.param2').value.trim();
            const res = block.querySelector('.result').value.trim();
            
            // Проверка, что поля не пустые
            if (p1 && p2 && res) {
                // Добавляем массив [par1, par2, res]
                dataArray.push([p1, p2, res]);
            } else {
                isValid = false;
            }
        });

        if (!isValid) {
            alert("Пожалуйста, заполните все поля во всех тест-кейсах.");
            return;
        }

        if (dataArray.length === 0) {
            alert("Добавьте хотя бы один тест.");
            return;
        }

        // Превращаем массив в строку JSON и кладем в скрытое поле test_data
        document.getElementById('hidden-test-data').value = JSON.stringify(dataArray);
        
        // Теперь отправляем форму
        form.submit();
    });
});