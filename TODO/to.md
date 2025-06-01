1. # Set "Allowed host" in settings.py 
2. # DEBUG = FALSE
3. # Thorough review of cable_optimizer.py (remove rdwriteModule and database query + write to excel function)
4. # 'setting' parameters to be used for drum schedule e.g pre order/post-order, free wbs, seperate wbs etc.
5. # in tasks.py currently we are using : cables_data = pd.read_json(StringIO(cables), orient='records')
   # instead try cables_data = pd.DataFrame(input_payload['cables']) for most robust design

6. 