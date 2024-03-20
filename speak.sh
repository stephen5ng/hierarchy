#!/bin/bash -e

# Speak files in /tmp/sayfiles

IFS=$'\n' # Set IFS to newline to handle filenames with spaces
while true; do
    # sleep 10
    file_list=$(ls -rt /tmp/sayfiles)
    num_files=$(find /tmp/sayfiles -type f -name "*.*" | wc -l)

    speed=$((0 + num_files * 200 ))

    if [[ $num_files -gt 10 ]]; then
        echo "too many, playing beep"
        echo -e "\a"
        /bin/rm -f -v /tmp/sayfiles/*.
    else
        for file_info in $file_list; do
            echo "$file_info : $speed"
            # ls -lT "/tmp/sayfiles/${file_info}"
            if [[ "$file_info" =~ "." ]]; then
                say -i "$file_info" -r $speed
            else
                say -i "$file_info"
            fi
            rm -f "/tmp/sayfiles/${file_info}"
        done
    fi
done
