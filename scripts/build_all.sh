find /opt/bojemoi -name 'Dockerfile.*' | while read file; do
    dirname=$(echo "$file" | cut -d"/" -f 4)
      /opt/bojemoi/scripts/cccp.sh $dirname
done

