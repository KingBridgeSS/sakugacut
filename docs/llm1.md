当需要模型输出程序可处理的标准格式（主要是 JSON）而非自然语言时，可开启结构化输出能力，以支持标准化处理或展示。

通过配置 **text.format** 对象，指定模型输出 JSON 格式，还可以通过定义 JSON 结构，限定模型输出字段信息。

相较于通过提示词控制模型输出 JSON 格式，使用结构化输出能力具有以下优势：


* 输出可靠：输出结构符合预期数据类型，包括字段层级、名称、类型、顺序等，避免必要字段缺失或枚举值幻觉。

* 使用简单：通过 API 字段定义输出格式，提示词更加简单，无需在提示词中反复强调或使用强约束措辞。


<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">该能力尚在 beta 阶段，请谨慎在生产环境使用。</div>


<span id="0047487f"></span>
## 支持模型

250615及之后版本的大语言模型，如无特殊说明，默认支持 Responses API，方舟平台大语言模型列表，请参见：[结构化输出能力(beta)](https://www.volcengine.com/docs/82379/1330310#25b394c2)。

<span id="7503fb44"></span>
## API文档

[Responses API](https://www.volcengine.com/docs/82379/1569618)

<span id="607e37db"></span>
## json_object 模式

这段代码展示了如何利用 Responses API 实现 JSON Object 结构化输出。


<Tabs>
<Tab zoneid="RwB3oP8kc2" title="Curl">
<TabTitle>Curl</TabTitle>

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "doubao-seed-1-6-251015",
    "thinking": { "type": "disabled" },
    "text": {
      "format": {
        "type": "json_object"
      }
    },
    "input": [
      {
        "role": "system",
        "content": "你是一位专业的数学助教，收到用户提出的数学问题后，需以结构化 JSON 格式输出。返回的json中应包含explanation和answer字段"
      },
      {
        "role": "user",
        "content": "根号三的近似值是多少"
      }
    ]
  }'
```



</Tab>
<Tab zoneid="wC8fHCYf1T" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
from volcenginesdkarkruntime import Ark

api_key = os.getenv('ARK_API_KEY')

client = Ark(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)

response = client.responses.create(
    model="doubao-seed-1-6-251015", 
    input=[
        {"role": "system", "content": 
         "你是一位专业的数学助教，收到用户提出的数学问题后，需以结构化 JSON 格式输出。"
         "返回的 JSON 应该包含以下字段："
         "1. 'explanation'：对题目的详细推理和解题步骤，内容应简明易懂。"
         "2. 'answer'：最终的纯数值答案或结论。"
         "所有内容均用简体中文。请勿输出 JSON 以外的内容。"
        },
        {"role": "user", "content": "根号三的近似值是多少。"}
    ],
    text={"format":{"type": "json_object"}}
)

print(response)
```



</Tab>
<Tab zoneid="bEc3HSwAwP" title="Go">
<TabTitle>Go</TabTitle>

```Go
package main

import (
    "context"
    "fmt"
    "os"

    "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model/responses"
)

func main() {
    client := arkruntime.NewClientWithApiKey(
        // Get API Key：https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
        os.Getenv("ARK_API_KEY"),
        arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"),
    )
    ctx := context.Background()

    resp, err := client.CreateResponses(ctx, &responses.ResponsesRequest{
        Model: "doubao-seed-1-6-251015",
        Input: &responses.ResponsesInput{
            Union: &responses.ResponsesInput_ListValue{
                ListValue: &responses.InputItemList{ListValue: []*responses.InputItem{
                    {
                        Union: &responses.InputItem_EasyMessage{
                            EasyMessage: &responses.ItemEasyMessage{
                                Role: responses.MessageRole_system,
                                Content: &responses.MessageContent{Union: &responses.MessageContent_StringValue{StringValue: `"你是一位专业的数学助教，收到用户提出的数学问题后，需以结构化 JSON 格式输出。"
                                    "返回的 JSON 应该包含以下字段："
                                    "1. 'explanation'：对题目的详细推理和解题步骤，内容应简明易懂。"
                                    "2. 'answer'：最终的纯数值答案或结论。"
                                    "所有内容均用简体中文。请勿输出 JSON 以外的内容。"`}},
                            },
                        },
                    },
                    {
                        Union: &responses.InputItem_EasyMessage{
                            EasyMessage: &responses.ItemEasyMessage{
                                Role:    responses.MessageRole_user,
                                Content: &responses.MessageContent{Union: &responses.MessageContent_StringValue{StringValue: "根号三的近似值是多少。"}},
                            },
                        },
                    },
                }},
            },
        },
        Text: &responses.ResponsesText{Format: &responses.TextFormat{Type: responses.TextType_json_object}}, 
    })
    if err != nil {
        fmt.Printf("stream error: %v", err)
        return
    }
    fmt.Println(resp)
}
```



</Tab>
<Tab zoneid="xPJn8crbfI" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.ark.example;
import com.volcengine.ark.runtime.model.responses.common.*;
import com.volcengine.ark.runtime.model.responses.item.ItemEasyMessage;
import com.volcengine.ark.runtime.service.ArkService;
import com.volcengine.ark.runtime.model.responses.request.*;
import com.volcengine.ark.runtime.model.responses.response.ResponseObject;
import com.volcengine.ark.runtime.model.responses.constant.ResponsesConstants;
import com.volcengine.ark.runtime.model.responses.item.MessageContent;
import com.volcengine.ark.runtime.model.responses.common.ResponsesTextFormat;


public class demo {
    public static void main(String[] args) {
        String apiKey = System.getenv("ARK_API_KEY");
        // The base URL for model invocation
        ArkService arkService = ArkService.builder().apiKey(apiKey).baseUrl("https://ark.cn-beijing.volces.com/api/v3").build();

        CreateResponsesRequest request = CreateResponsesRequest.builder()
                .model("doubao-seed-1-6-251015")
                .input(ResponsesInput.builder()
                        .addListItem(ItemEasyMessage.builder().role(ResponsesConstants.MESSAGE_ROLE_SYSTEM).content(
                                MessageContent.builder().stringValue("你是一位专业的数学助教，收到用户提出的数学问题后，需以结构化 JSON 格式输出。返回的json中应包含explanation和answer字段").build()
                        ).build())
                        .addListItem(ItemEasyMessage.builder().role(ResponsesConstants.MESSAGE_ROLE_USER).content(
                                MessageContent.builder().stringValue("根号三的近似值是多少").build()
                        ).build())
                        .build())
                .text(ResponsesText.builder().format(ResponsesTextFormat.builder().type(ResponsesConstants.TEXT_TYPE_JSON_OBJECT).build()).build())
                .build();
        ResponseObject resp = arkService.createResponse(request);
        System.out.println(resp);

        arkService.shutdownExecutor();
    }
}
```



</Tab>
<Tab zoneid="eo7ajl9AX0" title="OpenAI SDK">
<TabTitle>OpenAI SDK</TabTitle>

```Python
import os
from openai import OpenAI

api_key = os.getenv('ARK_API_KEY')

client = OpenAI(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)

response = client.responses.create(
    model="doubao-seed-1-6-251015", 
    input=[
        {"role": "system", "content": 
         "你是一位专业的数学助教，收到用户提出的数学问题后，需以结构化 JSON 格式输出。"
        "返回的 JSON 应该包含以下字段："
        "1. 'explanation'：对题目的详细推理和解题步骤，内容应简明易懂。"
        "2. 'answer'：最终的纯数值答案或结论。"
        "所有内容均用简体中文。请勿输出 JSON 以外的内容。"
        },
        {"role": "user", "content": "根号三的近似值是多少。"}
    ],
    text={"format":{"type": "json_object"}}
)

print(response)
```



</Tab>
</Tabs>


返回预览

```JSON
{
    "explanation": "根号三即√3，其近似值可通过逐步逼近法确定。首先，1²=1，2²=4，故√3在1和2之间。进一步计算，1.7²=2.89，1.8²=3.24，因此√3在1.7和1.8之间。继续精确，1.73²=2.9929，1.732²=2.999824（接近3），1.7321²≈3.00017（略大于3）。综上，√3的近似值通常取1.732。", 
    "answer": "1.732"
}
```


<span id="f4619f55"></span>
## json_schema 模式

这段代码展示了如何利用 Responses API 实现遵循 schema 字段定义的 JSON 结构化输出。


<Tabs>
<Tab zoneid="CHLPIiC0Dq" title="Curl">
<TabTitle>Curl</TabTitle>

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -d '{
    "model": "doubao-seed-1-6-251015",
    "input": [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "return in json format how can I solve 8x + 7 = -23"
                }
            ]
        }
    ],
    "thinking": {
        "type": "disabled"
    },
    "stream": false,
    "text": {
        "format": {
            "type": "json_schema",
            "name": "math_reasoning",
            "schema": {
                "type": "object",
                "properties": {
                    "steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "explanation": {
                                    "type": "string"
                                },
                                "output": {
                                    "type": "string"
                                }
                            },
                            "required": [
                                "explanation",
                                "output"
                            ],
                            "additionalProperties": false
                        }
                    },
                    "final_answer": {
                        "type": "string"
                    }
                },
                "required": [
                    "steps",
                    "final_answer"
                ],
                "additionalProperties": false
            }
        }
    }
  }'
```



</Tab>
<Tab zoneid="QYiT4IYWnx" title="OpenAI SDK">
<TabTitle>OpenAI SDK</TabTitle>

```Python
import os
from openai import OpenAI
from pydantic import BaseModel
api_key = os.getenv('ARK_API_KEY')

client = OpenAI(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)
class Step(BaseModel):
    explanation: str  # Step details
    output: str       # Step computation results

class MathResponse(BaseModel):
    steps: list[Step]       # List of solution steps
    final_answer: str       # Final answer
response = client.responses.parse(
    model="doubao-seed-1-6-251015", 
    input=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "return in json format how can I solve 8x + 7 = -23"
                }
            ]
        }
    ],
    text_format=MathResponse
)

print(response.output_parsed)
```



</Tab>
</Tabs>


返回预览

```JSON
{
    "steps": [
        {
            "explanation": "Subtract 7 from both sides to isolate the term with x",
            "output": "8x = -23 - 7"
        },
        {
            "explanation": "Simplify the right side",
            "output": "8x = -30"
        },
        {
            "explanation": "Divide both sides by 8 to solve for x",
            "output": "x = -30/8"
        },
        {
            "explanation": "Simplify the fraction",
            "output": "x = -15/4"
        }
    ],
    "final_answer": "x = -15/4"
}
```


<span id="f5afc902"></span>
## 模式对比：`json_object` 与 `json_schema`

`json_schema` 是 `json_object` 的演进版本，两种模式都支持 JSON 结构化输出，具体的异同如下。


<span aceTableMode="list" aceTableWidth="1,2,2"></span>
|结构化输出 |`json_schema` |`json_object` |
|---|---|---|
|生成 JSON 回复 |是 |是 |
|可定义 JSON 结构 |是 |否<br><br>仅保障回复是合法 JSON |
|是否推荐 |是 |否 |
|支持的模型 |见[结构化输出能力(beta)](https://www.volcengine.com/docs/82379/1330310#25b394c2) |见[结构化输出能力(beta)](https://www.volcengine.com/docs/82379/1330310#25b394c2) |
|严格模式 |支持<br><br>通过设置 **strict** 为 `true` 生效。 |不涉及 |
|配置方式 |```JSON```<br>```"text": {```<br>```    "format": {```<br>```        "type": "json_schema",```<br>```        "name": "my_schema",```<br>```        "strict": true,```<br>```        "schema": {```<br>```            ...```<br>```        }```<br>```    }```<br>```}```<br> |```JSON```<br>```"text": {```<br>```  "format": {```<br>```    "type": "json_object"```<br>```  }```<br>```}```<br> |


<span id="b9885e72"></span>
## 使用限制


* 使用[在线推理（TPM 保障包）](https://www.volcengine.com/docs/82379/1510762)时，不支持使用结构化输出能力。

* `doubao-seed-1.8` 之前版本，通过[模型单元概述](https://www.volcengine.com/docs/82379/1568332)部署模型进行在线推理时，不支持使用结构化输出能力。

* Responses API QPS 限流如下。如果需要提升限流值，请提交[工单](https://console.volcengine.com/workorder/create?step=2&SubProductID=P00001166)。



<span aceTableMode="list" aceTableWidth="1,1"></span>
|接口名称 |账号维度的 QPS 限流 |
|---|---|
|创建模型响应 |无 |
|查询模型响应 |20 |
|列出输入项 |20 |
|删除模型响应 |20 |




