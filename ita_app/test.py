


from datetime import datetime


start_date = ("")
end_date = ("")
            #format_string = "'%Y-%m-%d"
            #start_datetime = datetime.strptime(start_date, format_string)
            #end_datetime = datetime.strptime(end_date, format_string)
            #duration = start_datetime - end_datetime
start = datetime.fromisoformat(start_date)
end = datetime.fromisoformat(end_date)
duration = (end - start).days + 1  # +1 si inclusif