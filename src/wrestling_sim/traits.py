"""Structured physical traits. Names are flavor; numerical impact is contextual."""
TRAITS={'giant','big_man','small_underdog','powerhouse','combat_sports','masked',
        'wrestling_royalty','luchador','technical_purist','daredevil','veteran_mentor',
        'showman','submission_specialist','second_generation','antihero','locker_room_leader',
        'cult_favourite','prodigy','hardcore_specialist','natural_villain'}

def starting_profile(wid, attrs, age):
    # Stable fictional designs, no inference about actual individuals.
    specs={'steel':(191,112,['powerhouse','natural_villain','veteran_mentor']),
           'phoenix':(182,86,['daredevil','prodigy','showman']),
           'vale':(178,76,['wrestling_royalty','showman']),
           'cruz':(166,64,['small_underdog','technical_purist','daredevil']),
           'collins':(175,73,['combat_sports','technical_purist']),
           'knox':(202,133,['big_man','powerhouse']),
           'storm':(198,125,['big_man','showman']),
           'haze':(168,67,['daredevil','luchador']),
           'ryder':(185,98,['veteran_mentor','antihero'])}
    if wid in specs:return specs[wid]
    import hashlib
    n=int(hashlib.sha256(wid.encode()).hexdigest()[:7],16)
    height=166+(n%33);weight=65+(n//11%55)
    traits=[]
    if height>=194:traits.append('big_man')
    if height<=169:traits.append('small_underdog')
    if attrs.get('technique',0)>=22:traits.append('technical_purist')
    if attrs.get('agility',0)>=22:traits.append('daredevil')
    if age>=36:traits.append('veteran_mentor')
    if not traits:traits=['showman' if attrs.get('charisma',0)>20 else 'powerhouse']
    return height,weight,traits
