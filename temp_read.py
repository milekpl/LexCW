with open('app/templates/entry_form.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i in range(869, 1100):
        print(f"{i+1:4d}: {lines[i]}", end='')
