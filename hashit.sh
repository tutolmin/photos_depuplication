#!/bin/bash

# Создаём целевую директорию, если её не существует
mkdir -p ./src

# Рекурсивно ищем все .jpg файлы
find ./raw -type f -iname "*.jpg" -print0 | while IFS= read -r -d '' file; do
    # Вычисляем MD5 хеш файла
    md5_hash=$(md5sum "$file" | awk '{print $1}')
    
    # Формируем новое имя файла
    new_name="./src/${md5_hash}.jpg"
    
    echo "Обработка: $file"
    echo "MD5: $md5_hash"
    
    # Проверяем, существует ли уже файл с таким хешем в src
    if [[ -f "$new_name" ]]; then
        echo "  Предупреждение: файл с хешем $md5_hash уже существует. Пропускаем: $file"
        # Опционально: удалить исходный файл как дубликат
        rm -f "$file"
    else
        # Перемещаем файл
        mv "$file" "$new_name"
        echo "  Перемещён в: $new_name"
    fi
done
