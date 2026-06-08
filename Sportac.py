# ВРЕМЕННАЯ ДИАГНОСТИКА — удалить после отладки
html_snippet = await page.evaluate('''() => {
    const rows = document.querySelectorAll("tr");
    const result = [];
    for (let i = 0; i < Math.min(rows.length, 10); i++) {
        result.push(rows[i].innerHTML.substring(0, 200));
    }
    return result;
}''')
for i, h in enumerate(html_snippet):
    print(f"ROW {i}: {h}")
