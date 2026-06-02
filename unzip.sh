#!/bin/bash

find . -type f -iname "*.zip" -print0 | while IFS= read -r -d '' zipfile; do
    # Получаем директорию архива
    zipdir=$(dirname "$zipfile")
    
    # Создаём временную папку РЯДОМ с архивом (не в /tmp)
    # Шаблон: .tmp_XXXXXX - скрытая папка
    tempdir=$(mktemp -d -p "$zipdir" .tmp_XXXXXX)
    
    echo "Обработка: $zipfile"
    echo "Распаковка в: $tempdir"
    
    # Распаковываем архив во временную папку
#    if unzip -q "$zipfile" -d "$tempdir"; then
    if 7z x -o"$tempdir" "$zipfile"; then
        # Успех - удаляем архив
        rm -f "$zipfile"
        echo "Архив удалён: $zipfile"
        
        # Опционально: перемещаем содержимое временной папки на место архива
        # mv "$tempdir"/* "$zipdir"/ 2>/dev/null
        # rmdir "$tempdir"
    else
        # Ошибка распаковки - чистим за собой
        echo "ОШИБКА: не удалось распаковать $zipfile" >&2
        rm -rf "$tempdir"
    fi
done
