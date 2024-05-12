from openai import OpenAI

class Summerize():
  def summerize(self,input):
    client = OpenAI()
    response = client.chat.completions.create(
      model="gpt-3.5-turbo-0125",
      response_format={ "type": "json_object" },
      messages=[
        {"role": "system", "content": "I need you to summerize IN GREEK the following text limit it to 280 characters and don't present it as a summary but in first person,     return output JSON with key named output"},
        {"role": "user", "content": input }
    ]
    )
    return response.choices[0].message.content
if __name__ == "__main__":
  from Fek_getter import Fek_getter
  import json
  fek_object=Fek_getter()
  pdf_obj=fek_object.get_fek()
  input=pdf_obj[0]
  sum=Summerize()
  jsonobj=sum.summerize(input)
  print(jsonobj)
  print(type(jsonobj))
  diction=json.loads(jsonobj)
  print(diction['output'])