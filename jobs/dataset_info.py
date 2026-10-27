"""Grounded dataset discovery, separate from time-bound analytical questions."""
import re


def unavailable_product_categories(question, schema):
    """A missing product taxonomy cannot be supplied by choosing a time range."""
    text=question.lower()
    requested=bool(re.search(r'หมวดหมู่|หมวดสินค้า|ประเภทสินค้า|categor(?:y|ies)|taxonomy',text))
    product=bool(re.search(r'สินค้า|products?|items?',text))
    if not (requested and product):return None
    columns=set(re.findall(r'(?:<|,)([a-zA-Z_][a-zA-Z_0-9]*):',schema.get('sales_lines','')))
    if not columns or columns & {'category','category_id','product_category','category_name'}:return None
    thai=bool(re.search(r'[\u0e00-\u0e7f]',question))
    message=(
        'ชุดข้อมูลนี้ไม่มีหมวดหมู่สินค้า มีเพียงรหัสสินค้า (product_id) และคำอธิบายสินค้า (description) '
        'จึงยังแสดงหมวดหมู่หรือวิเคราะห์ยอดขายตามหมวดหมู่ไม่ได้ และไม่ควรเดาหมวดจากชื่อสินค้า '
        'หากต้องการใช้งาน ต้องเพิ่มตารางจับคู่รหัสสินค้ากับหมวดหมู่ที่ตรวจสอบแล้ว '
        'ขณะนี้สามารถวิเคราะห์รายสินค้าได้ เช่น “เดือนมกราคม 2011 สินค้าใดขายได้จำนวนมากที่สุด”'
        if thai else
        'This dataset has no product categories. It contains product_id and description, '
        'so category listings or category-level analytics are unavailable. Descriptions are not verified categories. '
        'A validated product-to-category mapping is required. You can analyze individual products instead, '
        'for example: Which products sold the most units in January 2011?')
    return {'status':'information','intent':'unavailable_product_categories','message':message,
            'model_calls':0,'attempts':[],'sql_executed':False,'citations':['schema.sales_lines']}


def is_dataset_discovery(question):
    text=re.sub(r'[?？!.]+$','',question.strip().lower()).strip()
    return bool(re.fullmatch(
        r'(?:มีข้อมูลอะไร(?:บ้าง)?|มีข้อมูลเกี่ยวกับอะไรบ้าง|ข้อมูลมีอะไรบ้าง|'
        r'ดูข้อมูลที่มี|แนะนำข้อมูล|ถามอะไรได้บ้าง|ทำอะไรได้บ้าง|'
        r'what data (?:is available|do you have)|what (?:tables|datasets) (?:are available|do you have)|'
        r'what can (?:i ask|you do)|show (?:the )?(?:available tables|dataset overview))',text))


def overview(schema):
    metadata=schema.get('_dataset_metadata',{})
    descriptions={
        'sales_lines':('รายการสินค้าและประเภทธุรกรรม','หนึ่งรายการสินค้าในข้อมูลต้นทาง'),
        'orders':('ใบสั่งซื้อที่เป็นรายการขายสำเร็จ','หนึ่งใบสั่งซื้อ'),
        'customer_summary':('ข้อมูลสรุปพฤติกรรมและกลุ่มลูกค้า','หนึ่งลูกค้า ณ วัน snapshot')}
    rows=[]
    for table,(description,grain) in descriptions.items():
        if table in schema:
            columns=re.findall(r'(?:<|,)([a-zA-Z_][a-zA-Z_0-9]*):',schema[table])
            rows.append([table,description,grain,', '.join(columns)])
    start,end=metadata.get('observed_min_timestamp'),metadata.get('observed_max_timestamp')
    snapshot=metadata.get('as_of_date')
    message='มีข้อมูลสำหรับวิเคราะห์ยอดขาย คำสั่งซื้อ สินค้า และพฤติกรรมลูกค้า ดังตารางด้านล่าง'
    if start and end:message+=f'\nช่วงข้อมูลที่มีจริง: {start} ถึง {end}'
    if snapshot:message+=f'\nข้อมูลสรุปลูกค้าใช้ snapshot วันที่ {snapshot}'
    message+='\nลองถาม: “เดือนตุลาคม 2011 มีคำสั่งซื้อสำเร็จกี่ใบ” หรือ “ยอดขายรวมเดือนมกราคม 2011 เท่าไร”'
    if not rows:message='ยังไม่มี schema ที่โหลดสำเร็จ จึงยังสรุปตารางที่ใช้งานได้ไม่ได้'
    return {'status':'information','message':message,
            'result':{'columns':['ตาราง','มีข้อมูลอะไร','หนึ่งแถวแทนอะไร','คอลัมน์ที่โหลดจริง'],
                      'rows':rows,'truncated':False},
            'source':'loaded_schema_and_dataset_manifest','model_calls':0,'attempts':[],
            'sql_executed':False}


def localize_policy(message, citation, question, metadata):
    if not re.search(r'[\u0e00-\u0e7f]',question):return message
    if citation=='policy.period':
        if 'metric' in message.lower():
            return 'ต้องการจัดอันดับลูกค้าด้วยเกณฑ์ใด เช่น ยอดขายหรือจำนวนคำสั่งซื้อ และใช้ช่วงเวลาหรือวัน snapshot ใด?'
        return 'ต้องการวิเคราะห์ช่วงเวลาใดครับ? ระบุเดือนและปี หรือวันที่เริ่มต้นและสิ้นสุด เช่น “ตุลาคม 2011”'
    if citation=='policy.snapshot':
        available=metadata.get('as_of_date')
        if 'unavailable' in message.lower():return f'ขณะนี้มีข้อมูลสรุปลูกค้าเฉพาะ snapshot วันที่ {available} ยังไม่มีวันที่ที่ขอ'
        return 'ต้องการใช้ข้อมูลสรุปลูกค้า ณ วันที่ใดครับ? ระบุรูปแบบ YYYY-MM-DD'+(f' ขณะนี้มีวันที่ {available}' if available else '')
    if citation=='policy.availability':
        if re.search(r'profit|margin|cost|campaign|uplift|กำไร|ต้นทุน|แคมเปญ',question.lower()):
            return 'ชุดข้อมูลนี้ไม่มีต้นทุน กำไร หรือผลแคมเปญที่วัดจริง จึงยังตอบคำถามนี้ไม่ได้'
        return f'ช่วงเวลาที่ขออยู่นอกข้อมูลที่มีจริง ซึ่งอยู่ระหว่าง {metadata.get("observed_min_timestamp")} ถึง {metadata.get("observed_max_timestamp")}'
    return message
