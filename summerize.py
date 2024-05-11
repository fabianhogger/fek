from openai import OpenAI
from get_fek import Fek_getter

class Summerize():
  def summerize(self,input):
    client = OpenAI()
    response = client.chat.completions.create(
      model="gpt-3.5-turbo-0125",
      response_format={ "type": "json_object" },
      messages=[
        {"role": "system", "content": "I need you to summerize IN GREEK the following text limit it to 280 characters and don't present it as a summary but in first person,     return output JSON"},
        {"role": "user", "content": input }
    ]
    )
    print(response.choices[0].message.content)
fek_object=Fek_getter()
pdf_obj=fek_object.get_fek()
input=pdf_obj[0]
sum=Summerize()
sum.summerize(input)