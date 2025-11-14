document.addEventListener('DOMContentLoaded', () => {
  // --- Get all the necessary calculator elements ---
  const calculator = document.getElementById('appCalculator');
  const toggleBtn = document.getElementById('calculatorToggleBtn');
  const display = document.getElementById('calculatorDisplay');
  const keys = document.querySelector('.calculator-keys');
  const header = calculator.querySelector('.calculator-header');

  // --- A simple check to make sure the script is running and elements are found ---
  if (!calculator || !toggleBtn || !display || !keys || !header) {
    console.error("Calculator script couldn't find one or more required elements. Check IDs in base.html.");
    return; // Stop the script if elements are missing
  }
  
  console.log("Calculator script loaded and elements found successfully.");

  // --- Toggle Calculator Visibility ---
  toggleBtn.addEventListener('click', () => {
    const isVisible = calculator.style.display === 'block';
    calculator.style.display = isVisible ? 'none' : 'block';
  });

  // --- Calculator Logic ---
  let firstValue = '';
  let operator = '';
  let secondValue = '';
  let shouldResetDisplay = false;

  function clear() {
      firstValue = '';
      operator = '';
      secondValue = '';
      display.value = '';
      shouldResetDisplay = false;
  }

  function calculate() {
    // Prevent calculation if inputs are incomplete
    if (firstValue === '' || operator === '' || display.value === '') return;
    secondValue = display.value;

    const a = parseFloat(firstValue);
    const b = parseFloat(secondValue);

    if (isNaN(a) || isNaN(b)) {
        display.value = 'Error';
        return;
    }

    let result = '';
    switch (operator) {
      case '+': result = a + b; break;
      case '-': result = a - b; break;
      case '*': result = a * b; break;
      case '/': 
        if (b === 0) {
            display.value = 'Error';
            return;
        }
        result = a / b; 
        break;
      case '%': result = a % b; break;
    }
    display.value = parseFloat(result.toPrecision(15)); // Handle floating point issues
    firstValue = result.toString();
    secondValue = '';
    shouldResetDisplay = true;
  }

  function handleKeyPress(key) {
    if (display.value === 'Error') clear();
    
    if (!isNaN(key) || key === '.') { // Number or decimal
      if (shouldResetDisplay) {
        display.value = '';
        shouldResetDisplay = false;
      }
      // Prevent multiple decimals
      if (key === '.' && display.value.includes('.')) return;
      display.value += key;
    } else if (['+', '-', '*', '/', '%'].includes(key)) { // Operator
      if (display.value !== '') {
         calculate();
         firstValue = display.value;
         operator = key;
         shouldResetDisplay = true;
      }
    } else if (key === '=') {
      calculate();
    } else if (key === 'clear') {
      clear();
    } else if (key === 'backspace') {
      display.value = display.value.slice(0, -1);
    }
  }

  keys.addEventListener('click', (e) => {
    if (e.target.matches('button')) {
      handleKeyPress(e.target.dataset.key);
    }
  });

  // --- Keyboard Support ---
  document.addEventListener('keydown', (e) => {
    if (calculator.style.display !== 'block') return;
    
    const keyMap = {
      'Enter': '=', '=': '=', 'Escape': 'clear', 'Backspace': 'backspace',
      '0': '0', '1': '1', '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9',
      '+': '+', '-': '-', '*': '*', '/': '/', '%': '%', '.': '.'
    };
    if (keyMap[e.key] !== undefined) {
        e.preventDefault();
        handleKeyPress(keyMap[e.key]);
    }
  });

  // --- Drag and Drop Logic ---
  let isDragging = false;
  let offsetX, offsetY;

  header.addEventListener('mousedown', (e) => {
    isDragging = true;
    offsetX = e.clientX - calculator.offsetLeft;
    offsetY = e.clientY - calculator.offsetTop;
    header.style.cursor = 'grabbing';
  });

  document.addEventListener('mousemove', (e) => {
    if (isDragging) {
      calculator.style.left = `${e.clientX - offsetX}px`;
      calculator.style.top = `${e.clientY - offsetY}px`;
    }
  });

  document.addEventListener('mouseup', () => {
    isDragging = false;
    header.style.cursor = 'move';
  });
});