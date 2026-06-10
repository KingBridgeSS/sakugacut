部分大模型支持音频理解能力，可通过本地文件和音频 URL 方式传入音频，可对音频内容进行语义理解与解析，适用于语音内容转写、对话语义提取、音频内容审核、会议纪要生成、视频伴音分析等场景。

<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">方舟平台的新用户？获取 API Key 及 开通模型等准备工作，请参见 <a href="https://www.volcengine.com/docs/82379/1399008">快速入门</a>。</div>


<span id="5592bede"></span>
# 支持模型

请参见[音频理解能力](https://www.volcengine.com/docs/82379/1330310#9619c0ba)。

<span id="81aa1aca"></span>
# API接口


* [Responses API](https://www.volcengine.com/docs/82379/1569618)：支持音频作为输入进行分析。支持 File ID 方式进行音频理解，使用方式参见[Files API上传（推荐）](https://www.volcengine.com/docs/82379/2377589#dba3306f)。

* [Chat API](https://www.volcengine.com/docs/82379/1494384)：支持音频作为输入进行分析。


<span id="53197ce9"></span>
# 音频输入方式

支持的音频文件传入方式如下：


* 本地文件上传：

   * [Files API上传（推荐）](https://www.volcengine.com/docs/82379/2377589#dba3306f)：直接传入本地文件，音频文件大小不能超过 512 MB，适用于在多个请求中重复使用文件的场景。

   * [Base64编码传入](https://www.volcengine.com/docs/82379/2377589#607f74ca)：适用于文件体积较小的场景，音频文件大小不能超过 25 MB，音频时长不超过 120 分钟。

* [音频URL传入](https://www.volcengine.com/docs/82379/2377589#268050a0)：适用于文件已存在公网可访问 URL 的场景，音频文件大小不能超过 25 MB，音频时长不超过 120 分钟。


<span id="2af64e6b"></span>
## 本地文件上传

<span id="dba3306f"></span>
### **Files API上传（推荐）** 

建议优先使用 Files API 上传本地文件，不仅可以支持最大 512MB 文件的处理，还可以避免请求时重新上传内容，减少预处理导致的时延，同时可在多次请求中重复使用，节省公网下载时延。（当前Responses API支持该方式。）


> * 该方式上传的文件默认存储 7 天，存储有效期取值范围为1\-30天。

> * 如果需要实时获取分析内容，或者要规避复杂任务引发的客户端超时失败问题，可采用流式输出的方式，具体示例见[流式输出](https://www.volcengine.com/docs/82379/2377589#3fe052be)。


代码示例：


<Tabs>
<Tab zoneid="bp9ANBlwmN" title="Curl">
<TabTitle>Curl</TabTitle>

1. 上传音频文件获取File ID


```Bash
curl https://ark.cn-beijing.volces.com/api/v3/files \
-H "Authorization: Bearer $ARK_API_KEY" \
-F 'purpose=user_data' \
-F 'file=@/Users/doc/demo.mp3'
```



2. 在Responses API中引用File ID


```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
-H "Authorization: Bearer $ARK_API_KEY" \
-H 'Content-Type: application/json' \
-d '{
    "model": "doubao-seed-2-0-lite-260428",
    "input": [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "file_id": "file-20260415****"
                },
                {
                    "type": "input_text",
                    "text": "请识别音频中的内容，以文字形式返回识别结果。"
                }
            ]
        }
    ]
}'
```



* 按需替换 Model ID，查询 Model ID 参见 [模型列表](https://www.volcengine.com/docs/82379/1330310)。


</Tab>
<Tab zoneid="ByMGH9kf0M" title="Python">
<TabTitle>Python</TabTitle>

```Python
import asyncio
import os
from volcenginesdkarkruntime import AsyncArk

client = AsyncArk(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=os.getenv('ARK_API_KEY')
)

async def main():
    print("Upload auudio file")
    file = await client.files.create(
        # replace with your local video path
        file=open("/Users/doc/demo.mp3", "rb"),
        purpose="user_data",
    )

    # Wait for the file to finish processing
    await client.files.wait_for_processing(file.id)
    print(f"File uploaded：{file.id}")

    response = await client.responses.create(
        model="doubao-seed-2-0-lite-260428",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "file_id": file.id
                    },
                    {
                        "type": "input_text",
                        "text": "请识别音频中的内容，以文字形式返回识别结果。"
                    }
                ]
            }
        ]
    )
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
```



</Tab>
<Tab zoneid="n7L3OwcaVI" title="Go">
<TabTitle>Go</TabTitle>

```Go
package main

import (
    "context"
    "fmt"
    "os"
    "time"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model/file"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model/responses"
    "github.com/volcengine/volcengine-go-sdk/volcengine"
)

func main() {
        client := arkruntime.NewClientWithApiKey(
                // Get API Key：https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
                os.Getenv("ARK_API_KEY"),
                arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"),
        )
        ctx := context.Background()

        fmt.Println("----- upload audio file -----")
        // Open local audio file
        data, err := os.Open("/Users/doc/demo.mp3")
        if err != nil {
                fmt.Printf("open audio file error: %v\n", err)
                return
        }

        fileInfo, err := client.UploadFile(ctx, &file.UploadFileRequest{
                File:    data,
                Purpose: file.PurposeUserData,
                // Audio does not need video preprocessing configs
        })

        if err != nil {
                fmt.Printf("upload audio file error: %v", err)
                return
        }

        // Wait for the file to finish processing
        for fileInfo.Status == file.StatusProcessing {
                fmt.Println("Waiting for audio to be processed...")
                time.Sleep(2 * time.Second)
                fileInfo, err = client.RetrieveFile(ctx, fileInfo.ID) // update file info
                if err != nil {
                        fmt.Printf("get file status error: %v", err)
                        return
                }
        }
        fmt.Printf("Audio processing completed: %s, status: %s\n", fileInfo.ID, fileInfo.Status)

        // Construct user input: audio file + text prompt
        inputMessage := &responses.ItemInputMessage{
                Role: responses.MessageRole_user,
                Content: []*responses.ContentItem{
                        {
                                Union: &responses.ContentItem_Audio{
                                        Audio: &responses.ContentItemAudio{
                                                Type:   responses.ContentItemType_input_audio,
                                                FileId: volcengine.String(fileInfo.ID),
                                        },
                                },
                        },
                        {
                                Union: &responses.ContentItem_Text{
                                        Text: &responses.ContentItemText{
                                                Type: responses.ContentItemType_input_text,
                                                Text: "请识别音频中的内容，以文字形式返回识别结果。",
                                        },
                                },
                        },
                },
        }

        // Build responses API request
        createResponsesReq := &responses.ResponsesRequest{
                Model: "doubao-seed-2-0-lite-260428", 
                Input: &responses.ResponsesInput{
                        Union: &responses.ResponsesInput_ListValue{
                                ListValue: &responses.InputItemList{
                                        ListValue: []*responses.InputItem{{
                                                Union: &responses.InputItem_InputMessage{
                                                        InputMessage: inputMessage,
                                                },
                                        }},
                                },
                        },
                },
                Caching: &responses.ResponsesCaching{Type: responses.CacheType_enabled.Enum()},
        }

        resp, err := client.CreateResponses(ctx, createResponsesReq)
        if err != nil {
                fmt.Printf("create responses error: %v\n", err)
                return
        }
        fmt.Println(resp)
}
```



</Tab>
<Tab zoneid="rGcY7nk2hU" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.ark.sample;

import com.volcengine.ark.runtime.model.files.FileMeta;
import com.volcengine.ark.runtime.model.files.UploadFileRequest;
import com.volcengine.ark.runtime.service.ArkService;
import com.volcengine.ark.runtime.model.responses.request.*;
import com.volcengine.ark.runtime.model.responses.item.ItemEasyMessage;
import com.volcengine.ark.runtime.model.responses.constant.ResponsesConstants;
import com.volcengine.ark.runtime.model.responses.item.MessageContent;
import com.volcengine.ark.runtime.model.responses.content.InputContentItemAudio;
import com.volcengine.ark.runtime.model.responses.content.InputContentItemText;
import com.volcengine.ark.runtime.model.responses.response.ResponseObject;
import java.io.File;
import java.util.concurrent.TimeUnit;

public class Demo {
    public static void main(String[] args) {
        String apiKey = System.getenv("ARK_API_KEY");
        ArkService service = ArkService.builder()
                .apiKey(apiKey)
                .baseUrl("https://ark.cn-beijing.volces.com/api/v3")
                .build();

        System.out.println("===== Upload Audio File Example =====");
        FileMeta fileMeta;
        fileMeta = service.uploadFile(
                UploadFileRequest.builder()
                        .file(new File("/Users/doc/demo.mp3")) // Replace with your local audio file path
                        .purpose("user_data")
                        .build());
        System.out.println("Uploaded file Meta: " + fileMeta);
        System.out.println("status: " + fileMeta.getStatus());

        try {
            while (fileMeta.getStatus().equals("processing")) {
                System.out.println("Waiting for audio to be processed...");
                TimeUnit.SECONDS.sleep(2);
                fileMeta = service.retrieveFile(fileMeta.getId());
            }
        } catch (Exception e) {
            System.err.println("get file status error: " + e.getMessage());
        }
        System.out.println("Processed file Meta: " + fileMeta);

        CreateResponsesRequest request = CreateResponsesRequest.builder()
                .model("doubao-seed-2-0-lite-260428") 
                .input(ResponsesInput.builder().addListItem(
                        ItemEasyMessage.builder()
                                .role(ResponsesConstants.MESSAGE_ROLE_USER)
                                .content(MessageContent.builder()
                                        // Add audio content with uploaded file ID
                                        .addListItem(InputContentItemAudio.builder().fileId(fileMeta.getId()).build())
                                        // Add text instruction for audio recognition
                                        .addListItem(InputContentItemText.builder()
                                                .text("请识别音频中的内容，以文字形式返回识别结果。")
                                                .build())
                                        .build()
                                ).build()
                ).build())
                .build();
        ResponseObject resp = service.createResponse(request);
        System.out.println(resp);

        service.shutdownExecutor();
    }
}
```



</Tab>
<Tab zoneid="Vv26usryg9" title="OpenAI SDK">
<TabTitle>OpenAI SDK</TabTitle>

```Python
import os
import time
from openai import OpenAI

api_key = os.getenv('ARK_API_KEY')

client = OpenAI(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)

file = client.files.create(
    file=open("/Users/doc/demo.mp3", "rb"),
    purpose="user_data"
)

# Wait for the file to finish processing
while file.status == "processing":
    time.sleep(2)
    file = client.files.retrieve(file.id)
print(f"File processed: {file.id}")

response = client.responses.create(
    model="doubao-seed-2-0-lite-260428",
    input=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "file_id": file.id,
                },
                {
                    "type": "input_text",
                    "text": "请识别音频中的内容，以文字形式返回识别结果。"
                },
            ]
        }
    ]
)

print(response)
```



</Tab>
</Tabs>


<span id="607f74ca"></span>
### Base64编码传入

将本地文件转换为 Base64 编码字符串，然后提交给大模型。该方式适用于音频文件体积较小的情况，音频文件大小不能超过 25 MB，音频时长不超过 120 分钟。（Responses API 和 Chat API 都支持该方式。）

<div data-tips="true" data-tips-type="warning" data-tips-is-title="true">注意</div>


<div data-tips="true" data-tips-type="warning">使用 Base64 编码传入音频时，需根据不同的 API 类型对数据格式进行处理：</div>



* <div data-tips="true" data-tips-type="warning">Responses API：遵循<code>data:{mime_type};base64,{base64_data}</code>格式拼接，通过<code>audio_url</code>字段传入模型。<code>{mime_type}</code>：文件的媒体类型，需要与文件格式<code>mime_type</code>对应。支持的音频格式详细见音频格式说明。<code>{base64_data}</code>：文件经过Base64编码后的字符串。</div>


* <div data-tips="true" data-tips-type="warning">Chat API：直接将 Base64 编码后的音频数据<code>{base64_data}</code>填入 <code>input_audio.data</code>，音频格式（如 mp3/wav）通过 <code>input_audio.format</code> 字段单独指定。</div>


* 使用 Responses API 的示例代码如下：



<Tabs>
<Tab zoneid="jOf6M2aMf2" title="Curl">
<TabTitle>Curl</TabTitle>

```Bash
BASE64_FILE=$(base64 < /Users/doc/demo.mp3) && curl https://ark.cn-beijing.volces.com/api/v3/responses \
   -H "Content-Type: application/json"  \
   -H "Authorization: Bearer $ARK_API_KEY"  \
   -d @- <<EOF
   {
    "model": "doubao-seed-2-0-lite-260428",
    "input": [
      {
        "role": "user",
        "content": [
          {
            "type": "input_audio",
            "audio_url": "data:audio/mpeg;base64,$BASE64_FILE"
          },
          {
            "type": "input_text",
            "text": "请识别音频中的内容"
          }
        ]
      }
    ]
  }
EOF
```



* 将 /Users/doc/demo.mp3 替换为你自己的音频路径。

* 按需替换 Model ID，查询 Model ID 参见 [模型列表](https://www.volcengine.com/docs/82379/1330310)。


</Tab>
<Tab zoneid="ZihkQWcS8d" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
from volcenginesdkarkruntime import Ark
import base64

api_key = os.getenv('ARK_API_KEY')

client = Ark(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)

# Convert local audio file to Base64-encoded string
def encode_file(file_path):
    with open(file_path, "rb") as read_file:
        return base64.b64encode(read_file.read()).decode('utf-8')

base64_file = encode_file("/Users/doc/demo.mp3")

response = client.responses.create(
    model="doubao-seed-2-0-lite-260428",
    input=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "audio_url": f"data:audio/mpeg;base64,{base64_file}"
                },
                {
                    "type": "input_text",
                    "text": "请识别音频中的内容"
                }
            ]
        }
    ]
)

print(response)
```



</Tab>
<Tab zoneid="WJvgWJGGiI" title="Go">
<TabTitle>Go</TabTitle>

```Go
package main

import (
    "context"
    "encoding/base64"
    "fmt"
    "os"

    "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model/responses"
)

func main() {
    // Convert local audio file to Base64-encoded strings.
    fileBytes, err := os.ReadFile("/Users/doc/demo.mp3")
    if err != nil {
        fmt.Printf("read audio file error: %v\n", err)
        return
    }
    base64File := base64.StdEncoding.EncodeToString(fileBytes)

    client := arkruntime.NewClientWithApiKey(
        os.Getenv("ARK_API_KEY"),
        arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"),
    )
    ctx := context.Background()

    inputMessage := &responses.ItemInputMessage{
        Role: responses.MessageRole_user,
        Content: []*responses.ContentItem{
            {
                Union: &responses.ContentItem_Audio{
                    Audio: &responses.ContentItemAudio{
                        Type:     responses.ContentItemType_input_audio,
                        AudioUrl: fmt.Sprintf("data:audio/mpeg;base64,%s", base64File),
                    },
                },
            },
            {
                Union: &responses.ContentItem_Text{
                    Text: &responses.ContentItemText{
                        Type: responses.ContentItemType_input_text,
                        Text: "请识别音频中的内容",
                    },
                },
            },
        },
    }

    resp, err := client.CreateResponses(ctx, &responses.ResponsesRequest{
        Model: "doubao-seed-2-0-lite-260428",
        Input: &responses.ResponsesInput{
            Union: &responses.ResponsesInput_ListValue{
                ListValue: &responses.InputItemList{ListValue: []*responses.InputItem{{
                    Union: &responses.InputItem_InputMessage{
                        InputMessage: inputMessage,
                    },
                }}},
            },
        },
    })
    if err != nil {
        fmt.Printf("audio recognition response error: %v\n", err)
        return
    }

    fmt.Println(resp)
}
```


Text: "请识别音频中的内容",


</Tab>
<Tab zoneid="Uy2VQAvUOM" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.ark.sample;

import com.volcengine.ark.runtime.model.responses.content.InputContentItemAudio;
import com.volcengine.ark.runtime.model.responses.content.InputContentItemText;
import com.volcengine.ark.runtime.model.responses.item.ItemEasyMessage;
import com.volcengine.ark.runtime.service.ArkService;
import com.volcengine.ark.runtime.model.responses.request.CreateResponsesRequest;
import com.volcengine.ark.runtime.model.responses.request.ResponsesInput;
import com.volcengine.ark.runtime.model.responses.response.ResponseObject;
import com.volcengine.ark.runtime.model.responses.constant.ResponsesConstants;
import com.volcengine.ark.runtime.model.responses.item.MessageContent;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Base64;
import java.io.IOException;

public class Sample {
    private static String encodeFile(String filePath) throws IOException {
        byte[] fileBytes = Files.readAllBytes(Paths.get(filePath));
        return Base64.getEncoder().encodeToString(fileBytes);
    }

    public static void main(String[] args) {
        String apiKey = System.getenv("ARK_API_KEY");
        ArkService arkService = ArkService.builder()
                .apiKey(apiKey)
                .baseUrl("https://ark.cn-beijing.volces.com/api/v3")
                .build();

        // Convert local audio file to Base64 data URL
        String base64AudioData = "";
        try {
            base64AudioData = "data:audio/mpeg;base64," + encodeFile("/Users/doc/demo.mp3");
        } catch (IOException e) {
            System.err.println("Encode audio file failed: " + e.getMessage());
            return;
        }

        CreateResponsesRequest request = CreateResponsesRequest.builder()
                .model("doubao-seed-2-0-lite-260428")
                .input(ResponsesInput.builder().addListItem(
                        ItemEasyMessage.builder()
                                .role(ResponsesConstants.MESSAGE_ROLE_USER)
                                .content(MessageContent.builder()
                                        // Add audio content with base64 URL
                                        .addListItem(InputContentItemAudio.builder().audioUrl(base64AudioData).build())
                                        // Add text instruction for audio recognition
                                        .addListItem(InputContentItemText.builder().text("请识别音频中的内容").build())
                                        .build()
                                ).build()
                ).build())
                .build();

        ResponseObject resp = arkService.createResponse(request);
        System.out.println(resp);

        arkService.shutdownExecutor();
    }
}
```



</Tab>
<Tab zoneid="H4G02GvxjJ" title="OpenAI SDK">
<TabTitle>OpenAI SDK</TabTitle>

```Python
import os
from openai import OpenAI
import base64

api_key = os.getenv('ARK_API_KEY')

client = OpenAI(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)

# Convert local files to Base64-encoded strings.
def encode_file(file_path):
  with open(file_path, "rb") as read_file:
    return base64.b64encode(read_file.read()).decode('utf-8')

# 音频文件路径
base64_file = encode_file("/Users/doc/demo.mp3")

response = client.responses.create(
    model="doubao-seed-2-0-lite-260428",
    input=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "audio_url": f"data:audio/mpeg;base64,{base64_file}"
                },
                {
                    "type": "input_text",
                    "text": "请识别音频中的内容"
                }
            ],
        }
    ]
)

print(response)
```



</Tab>
</Tabs>



* 使用 Chat API 的示例代码如下：



<Tabs>
<Tab zoneid="mYvuYYRugU" title="Curl">
<TabTitle>Curl</TabTitle>

```Bash
BASE64_VIDEO=$(base64 < /Users/doc/demo.mp3) && curl https://ark.cn-beijing.volces.com/api/v3/chat/completions \
   -H "Content-Type: application/json"  \
   -H "Authorization: Bearer $ARK_API_KEY"  \
   -d @- <<EOF
   {
    "model": "doubao-seed-2-0-lite-260428",
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "input_audio",
            "input_audio": {
                "data": "$BASE64_FILE",
                "format": "mp3"
                }
          },
          {
            "type": "text",
            "text": "请识别音频中的内容"
          }
        ]
      }
    ]
  }
EOF
```



* 将 /Users/doc/demo.mp3 替换为你自己的音频路径。

* 按需替换 Model ID，查询 Model ID 参见 [模型列表](https://www.volcengine.com/docs/82379/1330310)。


</Tab>
<Tab zoneid="ZHSdvw6Kss" title="Python">
<TabTitle>Python</TabTitle>

```Python
import base64
import os
# Install SDK:  pip install 'volcengine-python-sdk[ark]'
from volcenginesdkarkruntime import Ark

client = Ark(
    base_url="https://ark.cn-beijing.volces.com/api/v3", 
    api_key=os.getenv('ARK_API_KEY'), 
)

# 定义方法将指定路径音频转为Base64编码
def encode_audio(audio_path):
    with open(audio_path, "rb") as audio_file:
        return base64.b64encode(audio_file.read()).decode('utf-8')

# 需传给大模型的音频
audio_path = "/Users/doc/demo.mp3"

# 将音频转为Base64编码
base64_audio = encode_audio(audio_path)

completion = client.chat.completions.create(
    # Replace with Model ID
    model="doubao-seed-2-0-lite-260428",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": base64_audio,
                        "format": "mp3"
                    }
                },
                {
                    "type": "text",
                    "text": "请识别音频中的内容"
                },
            ],
        }
    ],
)

print(completion.choices[0])
```



</Tab>
<Tab zoneid="smwDfJORPC" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.ark.sample;

import com.volcengine.ark.runtime.model.completion.chat.*;
import com.volcengine.ark.runtime.model.completion.chat.ChatCompletionContentPart.*;
import com.volcengine.ark.runtime.service.ArkService;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;
import okhttp3.ConnectionPool;
import okhttp3.Dispatcher;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Base64;
import java.io.IOException;

public class Sample {
    static String apiKey = System.getenv("ARK_API_KEY");
    static ConnectionPool connectionPool = new ConnectionPool(5, 1, TimeUnit.SECONDS);
    static Dispatcher dispatcher = new Dispatcher();
    static ArkService service = ArkService.builder()
        .dispatcher(dispatcher)
        .connectionPool(connectionPool)
        .baseUrl("https://ark.cn-beijing.volces.com/api/v3")
        .apiKey(apiKey)
        .build();

    // 音频文件 Base64 编码（不带前缀，直接纯Base64）
    private static String encodeAudio(String audioPath) throws IOException {
        byte[] audioBytes = Files.readAllBytes(Path.of(audioPath));
        return Base64.getEncoder().encodeToString(audioBytes);
    }

    public static void main(String[] args) throws Exception {
        List<ChatMessage> messagesForReqList = new ArrayList<>();

        // 你的音频路径（改成自己实际路径）
        String audioPath = "/Users/doc/demo.mp3";
        // 音频Base64
        String base64Data = encodeAudio(audioPath);

        // 构建多模态内容
        List<ChatCompletionContentPart> contentParts = new ArrayList<>();

        // 音频部分（input_audio + data + format）
        ChatCompletionContentPartInputAudio inputAudio = new ChatCompletionContentPartInputAudio();
        inputAudio.setData(base64Data);
        inputAudio.setFormat("mp3");
        
        contentParts.add(ChatCompletionContentPart.builder()
                .type("input_audio")
                .inputAudio(inputAudio)
                .build());

        // 文本指令
        contentParts.add(ChatCompletionContentPart.builder()
                .type("text")
                .text("请识别音频中的内容")
                .build());

        // 构造用户消息
        messagesForReqList.add(ChatMessage.builder()
                .role(ChatMessageRole.USER)
                .multiContent(contentParts)
                .build());

        // 请求体
        ChatCompletionRequest req = ChatCompletionRequest.builder()
                .model("doubao-seed-2-0-lite-260428")
                .messages(messagesForReqList)
                .build();

        // 调用并打印结果
        service.createChatCompletion(req)
                .getChoices()
                .forEach(choice -> System.out.println(choice.getMessage().getContent()));

        service.shutdownExecutor();
    }
}
```



</Tab>
</Tabs>


<span id="268050a0"></span>
## 音频URL传入

如果音频文件已存在公网可访问URL，可以在请求中直接填入音频文件的公网URL，音频文件大小不能超过 25 MB，音频时长不超过 120 分钟。（Responses API 和 Chat API 都支持该方式。）


* 使用 Responses API 的示例代码如下：



<Tabs>
<Tab zoneid="cJrZuN6eeT" title="Curl">
<TabTitle>Curl</TabTitle>

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
-H "Authorization: Bearer $ARK_API_KEY" \
-H 'Content-Type: application/json' \
-d '{
    "model": "doubao-seed-2-0-lite-260428",
    "input": [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "audio_url": "https://ark-project.tos-cn-beijing.volces.com/doc_audio/ark_demo_audio.mp3"
                },
                {
                    "type": "input_text",
                    "text": "请识别这段音频内容"
                }
            ]
        }
    ]
}'
```



* 按需替换 Model ID，查询 Model ID 参见 [模型列表](https://www.volcengine.com/docs/82379/1330310)。


</Tab>
<Tab zoneid="uQqXf6AHfP" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
from volcenginesdkarkruntime import Ark

# Get API Key from environment variable
api_key = os.getenv('ARK_API_KEY')

client = Ark(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)

# Call responses API with audio URL input
response = client.responses.create(
    model="doubao-seed-2-0-lite-260428",
    input=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "audio_url": "https://ark-project.tos-cn-beijing.volces.com/doc_audio/ark_demo_audio.mp3"
                },
                {
                    "type": "input_text",
                    "text": "请识别这段音频内容"
                }
            ],
        }
    ]
)

print(response)
```



</Tab>
<Tab zoneid="A7JJq2Sw5z" title="Go">
<TabTitle>Go</TabTitle>

```Go
package main

import (
        "context"
        "fmt"
        "os"

        "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
        "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model/responses"
        "github.com/volcengine/volcengine-go-sdk/volcengine"
)

func main() {
        client := arkruntime.NewClientWithApiKey(
                // Get ARK_API_KEY from environment variable
                os.Getenv("ARK_API_KEY"),
                arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"),
        )
        ctx := context.Background()

        // Construct user input: audio URL + text prompt
        inputMessage := &responses.ItemInputMessage{
                Role: responses.MessageRole_user,
                Content: []*responses.ContentItem{
                        {
                                Union: &responses.ContentItem_Audio{
                                        Audio: &responses.ContentItemAudio{
                                                Type:     responses.ContentItemType_input_audio,
                                                AudioUrl: "https://ark-project.tos-cn-beijing.volces.com/doc_audio/ark_demo_audio.mp3",
                                        },
                                },
                        },
                        {
                                Union: &responses.ContentItem_Text{
                                        Text: &responses.ContentItemText{
                                                Type: responses.ContentItemType_input_text,
                                                Text: "请识别这段音频内容",
                                        },
                                },
                        },
                },
        }

        // Send request to CreateResponses API
        resp, err := client.CreateResponses(ctx, &responses.ResponsesRequest{
                Model: "doubao-seed-2-0-lite-260428",
                Input: &responses.ResponsesInput{
                        Union: &responses.ResponsesInput_ListValue{
                                ListValue: &responses.InputItemList{ListValue: []*responses.InputItem{{
                                        Union: &responses.InputItem_InputMessage{
                                                InputMessage: inputMessage,
                                        },
                                }}},
                        },
                },
        })
        if err != nil {
                fmt.Printf("response error: %v\n", err)
                return
        }
        fmt.Println(resp)
}
```



</Tab>
<Tab zoneid="FCJ1XECbJF" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.ark.example;

import com.volcengine.ark.runtime.model.responses.content.InputContentItemAudio;
import com.volcengine.ark.runtime.model.responses.content.InputContentItemText;
import com.volcengine.ark.runtime.model.responses.item.ItemEasyMessage;
import com.volcengine.ark.runtime.service.ArkService;
import com.volcengine.ark.runtime.model.responses.request.*;
import com.volcengine.ark.runtime.model.responses.response.ResponseObject;
import com.volcengine.ark.runtime.model.responses.constant.ResponsesConstants;
import com.volcengine.ark.runtime.model.responses.item.MessageContent;

public class demo {
    public static void main(String[] args) {
        String apiKey = System.getenv("ARK_API_KEY");
        ArkService arkService = ArkService.builder().apiKey(apiKey).baseUrl("https://ark.cn-beijing.volces.com/api/v3").build();

        CreateResponsesRequest request = CreateResponsesRequest.builder()
                .model("doubao-seed-2-0-lite-260428")
                .input(ResponsesInput.builder().addListItem(
                        ItemEasyMessage.builder().role(ResponsesConstants.MESSAGE_ROLE_USER).content(
                                MessageContent.builder()
                                        .addListItem(InputContentItemAudio.builder().audioUrl("https://ark-project.tos-cn-beijing.volces.com/doc_audio/ark_demo_audio.mp3").build())
                                        .addListItem(InputContentItemText.builder().text("请识别这段音频内容").build())
                                        .build()
                        ).build()
                ).build())
                .build();
        ResponseObject resp = arkService.createResponse(request);
        System.out.println(resp);

        arkService.shutdownExecutor();
    }
}
```



</Tab>
<Tab zoneid="RGE8HLTuKi" title="OpenAI SDK">
<TabTitle>OpenAI SDK</TabTitle>

```Python
import os
from openai import OpenAI

# 从环境变量中获取您的API KEY
api_key = os.getenv('ARK_API_KEY')

client = OpenAI(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)

response = client.responses.create(
    model="doubao-seed-2-0-lite-260428", 
    input=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "audio_url": "https://ark-project.tos-cn-beijing.volces.com/doc_audio/ark_demo_audio.mp3"
                },
                {
                    "type": "input_text",
                    "text": "请识别这段音频内容"
                }
            ]
        }
    ]
)

print(response)
```



</Tab>
</Tabs>



* 使用 Chat API 的示例代码如下：



<Tabs>
<Tab zoneid="Gfyffb1OLz" title="Curl">
<TabTitle>Curl</TabTitle>

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/chat/completions \
-H "Content-Type: application/json"  \
-H "Authorization: Bearer $ARK_API_KEY"  \
-d '{
    "model": "doubao-seed-2-0-lite-260428",
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "input_audio": {
                        "url": "https://ark-project.tos-cn-beijing.volces.com/doc_audio/ark_demo_audio.mp3",
                        "format": "mp3"
                    }
                },
                {
                    "type": "text",
                    "text": "请识别音频中的内容"
                }
            ]
        }
    ]
}'
```



* 按需替换 Model ID，查询 Model ID 参见 [模型列表](https://www.volcengine.com/docs/82379/1330310)。


</Tab>
<Tab zoneid="hBNl8MRUqM" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
# Install SDK:  pip install 'volcengine-python-sdk[ark]'
from volcenginesdkarkruntime import Ark

client = Ark(
    # The base URL for model invocation
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    # Get API Key：https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
    api_key=os.getenv('ARK_API_KEY'),
)

completion = client.chat.completions.create(
    # Replace with Model ID
    model = "doubao-seed-2-0-lite-260428",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "input_audio": {
                        "url": "https://ark-project.tos-cn-beijing.volces.com/doc_audio/ark_demo_audio.mp3",
                        "format": "mp3"
                    }
                },
                {"type": "text", "text": "请识别音频中的内容"},
            ],
        }
    ],
)

print(completion.choices[0])
```



</Tab>
<Tab zoneid="v8av4WCxQz" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.ark.sample;

import com.volcengine.ark.runtime.model.completion.chat.*;
import com.volcengine.ark.runtime.model.completion.chat.ChatCompletionContentPart.*;
import com.volcengine.ark.runtime.service.ArkService;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;
import okhttp3.ConnectionPool;
import okhttp3.Dispatcher;

public class Sample {
    static String apiKey = System.getenv("ARK_API_KEY");
    static ConnectionPool connectionPool = new ConnectionPool(5, 1, TimeUnit.SECONDS);
    static Dispatcher dispatcher = new Dispatcher();
    static ArkService service = ArkService.builder()
        .dispatcher(dispatcher)
        .connectionPool(connectionPool)
        .baseUrl("https://ark.cn-beijing.volces.com/api/v3")
        .apiKey(apiKey)
        .build();

    public static void main(String[] args) throws Exception {

        List<ChatMessage> messagesForReqList = new ArrayList<>();

        List<ChatCompletionContentPart> contentParts = new ArrayList<>();

        ChatCompletionContentPartInputAudio inputAudio = new ChatCompletionContentPartInputAudio();
        inputAudio.setUrl("https://ark-project.tos-cn-beijing.volces.com/doc_audio/ark_demo_audio.mp3");
        inputAudio.setFormat("mp3");

        contentParts.add(ChatCompletionContentPart.builder()
                .type("input_audio")
                .inputAudio(inputAudio)
                .build());

        contentParts.add(ChatCompletionContentPart.builder()
                .type("text")
                .text("请识别音频中的内容")
                .build());

        messagesForReqList.add(ChatMessage.builder()
                .role(ChatMessageRole.USER)
                .multiContent(contentParts)
                .build());

        ChatCompletionRequest req = ChatCompletionRequest.builder()
                .model("doubao-seed-2-0-lite-260428")
                .messages(messagesForReqList)
                .build();

        service.createChatCompletion(req)
                .getChoices()
                .forEach(choice -> System.out.println(choice.getMessage().getContent()));

        service.shutdownExecutor();
    }
}
```



</Tab>
</Tabs>


<span id="ee12cbb7"></span>
# **使用场景**

<span id="0a9900d2"></span>
## 视频内嵌音频输入

支持对视频中内嵌的音频轨道进行解析与语义理解。无需单独提取音频，可直接将完整视频作为输入，模型会自动抽取音轨并完成语音识别、内容理解、情感与语气分析等相关任务。具体使用格式与入参规范可参考[视频理解](https://www.volcengine.com/docs/82379/1895586)。

示例代码如下：


<Tabs>
<Tab zoneid="pS9XuN5I7X" title="Curl">
<TabTitle>Curl</TabTitle>

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
-H "Content-Type: application/json"  \
-H "Authorization: Bearer $ARK_API_KEY"  \
-d '{
    "model": "doubao-seed-2-0-lite-260428",
    "input": [
        {
            "role": "user",
            "content": [
                {    
                    "type": "input_video",
                    "video_url": "https://ark-project.tos-cn-beijing.volces.com/doc_video/video_by_sd2.mp4",
                    "fps": 1
                },
                {
                    "type": "input_text",
                    "text": "请识别视频中的音频内容，同时分析音频中的音色特点、说话人语气、语速及情感倾向，输出完整清晰的文本结果"
                }
            ]
        }
    ]
}'
```



* 按需替换 Model ID，查询 Model ID 参见 [模型列表](https://www.volcengine.com/docs/82379/1330310)。


</Tab>
<Tab zoneid="OxJYQjEZ2K" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
from volcenginesdkarkruntime import Ark
# 从环境变量中获取您的API KEY，配置方法见：https://www.volcengine.com/docs/82379/1399008
api_key = os.getenv('ARK_API_KEY')
client = Ark(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)
response = client.responses.create(
    model="doubao-seed-2-0-lite-260428",
    input=[
        {
            "role": "user",
            "content": [
                {    
                    "type": "input_video",
                    "video_url": "https://ark-project.tos-cn-beijing.volces.com/doc_video/video_by_sd2.mp4",
                    "fps":1
                },
                {
                    "type": "input_text",
                    "text": "请识别视频中的音频内容，同时分析音频中的音色特点、说话人语气、语速及情感倾向，输出完整清晰的文本结果"
                }
            ],
        }
    ]
)
print(response)
```



</Tab>
<Tab zoneid="jZGhVMNbdA" title="Go">
<TabTitle>Go</TabTitle>

```Go
package main
import (
    "context"
    "fmt"
    "os"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model/responses"
    "github.com/volcengine/volcengine-go-sdk/volcengine"
)
func main() {
    client := arkruntime.NewClientWithApiKey(
        //通过 os.Getenv 从环境变量中获取 ARK_API_KEY
        os.Getenv("ARK_API_KEY"),
        arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"),
    )
    // 创建一个上下文，通常用于传递请求的上下文信息，如超时、取消等
    ctx := context.Background()
    inputMessage := &responses.ItemInputMessage{
        Role: responses.MessageRole_user,
        Content: []*responses.ContentItem{
            {
                Union: &responses.ContentItem_Video{
                    Video: &responses.ContentItemVideo{
                        Type:     responses.ContentItemType_input_video,
                        VideoUrl: "https://ark-project.tos-cn-beijing.volces.com/doc_video/video_by_sd2.mp4",
                        Fps:      volcengine.Float32(1),
                    },
                },
            },
            {
                Union: &responses.ContentItem_Text{
                    Text: &responses.ContentItemText{
                        Type: responses.ContentItemType_input_text,
                        Text: "请识别视频中的音频内容，同时分析音频中的音色特点、说话人语气、语速及情感倾向，输出完整清晰的文本结果",
                    },
                },
            },
        },
    }
    resp, err := client.CreateResponses(ctx, &responses.ResponsesRequest{
        Model: "doubao-seed-2-0-lite-260428",
        Input: &responses.ResponsesInput{
            Union: &responses.ResponsesInput_ListValue{
                ListValue: &responses.InputItemList{ListValue: []*responses.InputItem{{
                    Union: &responses.InputItem_InputMessage{
                        InputMessage: inputMessage,
                    },
                }}},
            },
        },
    })
    if err != nil {
        fmt.Printf("response error: %v\n", err)
        return
    }
    fmt.Println(resp)
}
```



</Tab>
<Tab zoneid="fY2PMq6SOq" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.ark.example;
import com.volcengine.ark.runtime.model.responses.content.InputContentItemImage;
import com.volcengine.ark.runtime.model.responses.content.InputContentItemText;
import com.volcengine.ark.runtime.model.responses.content.InputContentItemVideo;
import com.volcengine.ark.runtime.model.responses.item.ItemEasyMessage;
import com.volcengine.ark.runtime.service.ArkService;
import com.volcengine.ark.runtime.model.responses.request.*;
import com.volcengine.ark.runtime.model.responses.response.ResponseObject;
import com.volcengine.ark.runtime.model.responses.constant.ResponsesConstants;
import com.volcengine.ark.runtime.model.responses.item.MessageContent;
public class demo {
    public static void main(String[] args) {
        String apiKey = System.getenv("ARK_API_KEY");
        // 创建ArkService实例
        ArkService arkService = ArkService.builder().apiKey(apiKey).baseUrl("https://ark.cn-beijing.volces.com/api/v3").build();
        CreateResponsesRequest request = CreateResponsesRequest.builder()
                .model("doubao-seed-2-0-lite-260428")
                .input(ResponsesInput.builder().addListItem(
                        ItemEasyMessage.builder().role(ResponsesConstants.MESSAGE_ROLE_USER).content(
                                MessageContent.builder()
                                        .addListItem(InputContentItemVideo.builder().videoUrl("https://ark-project.tos-cn-beijing.volces.com/doc_video/video_by_sd2.mp4").fps(2F).build())
                                        .addListItem(InputContentItemText.builder().text("请识别视频中的音频内容，同时分析音频中的音色特点、说话人语气、语速及情感倾向，输出完整清晰的文本结果").build())
                                        .build()
                        ).build()
                ).build())
                .build();
        ResponseObject resp = arkService.createResponse(request);
        System.out.println(resp);
        arkService.shutdownExecutor();
    }
}
```



</Tab>
<Tab zoneid="dboPALXDu3" title="OpenAI SDK">
<TabTitle>OpenAI SDK</TabTitle>

```Python
import os
from openai import OpenAI
# 从环境变量中获取您的API KEY，配置方法见：https://www.volcengine.com/docs/82379/1399008
api_key = os.getenv('ARK_API_KEY')
client = OpenAI(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)
response = client.responses.create(
    model="doubao-seed-2-0-lite-260428",
    input=[
        {
            "role": "user",
            "content": [
                {    
                    "type": "input_video",
                    "video_url": "https://ark-project.tos-cn-beijing.volces.com/doc_video/video_by_sd2.mp4",
                    "fps":1
                },
                {
                    "type": "input_text",
                    "text": "请识别视频中的音频内容，同时分析音频中的音色特点、说话人语气、语速及情感倾向，输出完整清晰的文本结果"
                }
            ],
        }
    ]
)
print(response)
```



</Tab>
</Tabs>


<span id="55908c54"></span>
## 通用音频理解问答

围绕音频内容开展开放式语义理解与智能问答，模型可完整解析音频信息，结合用户文本问题，输出结构化、可分析的专业回答。根据交互形式，分为两大子场景：单轮对话和多轮对话。

<span id="66620df1"></span>
### 单轮对话

采用一问一答的轻量化交互模式，适配音频类型判别、环境场景识别、内容细节查询、基础信息解读等轻量化诉求。

下面是简单示例代码

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "doubao-seed-2-0-lite-260428",
    "instructions": "你是音频理解专家，擅长分析音频信息来回答问题。",
    "input": [
      {
        "type": "message",
        "role": "user",
        "content": [
          {
              "type": "input_audio", 
              "audio_url": "https://ark-project.tos-cn-beijing.volces.com/doc_audio/audio_understanding_single_qa.wav"
          },
          {
              "type": "input_text", 
              "text": "我穿的是套头毛衣、T恤、夹克还是吊带？"
          }
        ]
      }
    ]
  }'
```


按需替换 Model ID，查询 Model ID 参见 [模型列表](https://www.volcengine.com/docs/82379/1330310)。

回复预览

```Plain
你穿的是夹克。这段音频里除了持续的整理揉搓衣料的摩擦声，还出现了两次非常典型的短促有力的长拉链拉动咬合声，套头毛衣、普通T恤、吊带都不存在这种需要操作前中长拉链的典型动作特征，这两声正是你整理完衣物后操作夹克拉链的声音。
```


<span id="a12f288d"></span>
### 多轮对话

适用于客服复盘、语言陪练、听力答疑等需连续交互的场景。在该场景下，用户可在每一轮交互中追加新的音频输入，模型将结合"历史全部音频 + 历史全部文本回复 + 本轮新问题"综合推理并输出全新的文本答复，确保对话上下文的连贯性与答复的准确性。

<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">Responses API 提供原生的多轮串联能力，客户端无需手动拼接历史。只需在请求里传入 <code>previous_response_id = <上一次响应的 id></code>，服务端会自动把前序所有 <code>input</code> 和 <code>assistant</code> 输出作为上下文继续推理。</div>


下面是简单示例代码


* 第一轮请求：用户上传第一段录音，询问人员情况


```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "doubao-seed-2-0-lite-260428",
    "instructions": "你是音频理解专家，擅长分析音频信息来回答问题。",
    "input": [
      {
        "type": "message",
        "role": "user",
        "content": [
          {
              "type": "input_audio", 
              "audio_url": "https://ark-project.tos-cn-beijing.volces.com/doc_audio/audio_demo_video_multispeaker_01.m4a"
          },
          {
              "type": "input_text", 
              "text": "这段录音里有几个人在说话？各自是什么性别和年龄段？"
          }
        ]
      }
    ]
  }'
```


按需替换 Model ID，查询 Model ID 参见 [模型列表](https://www.volcengine.com/docs/82379/1330310)。

第一轮响应：

```Bash
{
  "id": "resp_0217772771288531389853d7d0951ef6849890aa76b17cc5b65ac",
  "object": "response",
  "model": "doubao-seed-2-0-lite-260428",
  "output": [
    {
      "type": "message",
      "role": "assistant",
      "content": [
        {
          "type": "output_text",
          "text": "这段录音里一共有3名说话人，所有说话人都属于青年年龄段：\n1. 第一位是青年男性，声线偏浑厚，参与内容讨论；\n2. 第二位是青年女性，声线清亮，是内容的主要讲解者；\n3. 第三位是另一名青年男性，参与对话互动，验证相关内容的呈现效果。"
        }
      ]
    }
  ],
  "usage": {
    "input_tokens": 150,
    "output_tokens": 732,
    "total_tokens": 882
  }
}
```


记录响应体的 `id`（此处为 `resp_0217772771288531389853d7d0951ef6849890aa76b17cc5b65ac`），它将作为下一轮的 `previous_response_id`。


* 第二轮请求：追加第二段录音，询问情绪变化（使用 `previous_response_id` 串接上轮内容）


```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "doubao-seed-2-0-lite-260428",
    "previous_response_id": "resp_0217772771288531389853d7d0951ef6849890aa76b17cc5b65ac",
    "input": [
      {
        "type": "message",
        "role": "user",
        "content": [
          {
              "type": "input_audio", 
              "audio_url": "https://ark-project.tos-cn-beijing.volces.com/doc_audio/audio_demo_video_multispeaker_02.m4a"
          },
          {
              "type": "input_text", 
              "text": "这段还是刚才那三个人吗？他们的情绪相比上一段有什么变化？"
          }
        ]
      }
    ]
  }'
```


第二轮响应

```Bash
{
  "id": "resp_021777277730499f0fcebbb8d813ae358cfc99ccc356325bebca4",
  "object": "response",
  "model": "doubao-seed-2-0-lite-260428",
  "output": [
    {
      "type": "message",
      "role": "assistant",
      "content": [
        {
          "type": "output_text",
          "text": "这段依旧是之前的三位说话人，没有更换或新增参与者，还是2位青年男性+1位青年女性的组合。\n\n情绪变化非常明显：\n上一段对话里他们整体处于边操作边核验内容、核对排版和内容匹配度的状态，情绪偏向专注务实，只有确认内容匹配上了的浅层次的稳妥感；\n到了这段，他们的情绪直接从平稳的核验状态跳转到了亢奋愉悦的状态，完全被最终呈现的效果惊艳到，满是直白的夸赞，满是“效果远超预期、需求被完美满足”的畅快的满意感，氛围从之前偏严谨的核对感，变成了轻松雀跃的高度正向认可的氛围。"
        }
      ]
    }
  ],
  "previous_response_id": "resp_0217772771288531389853d7d0951ef6849890aa76b17cc5b65ac",
  "usage": {
    "input_tokens": 285,
    "output_tokens": 538,
    "total_tokens": 823
  }
}
```


<span id="e4eed248"></span>
## 音频分析（Caption）

依托大模型能力对音频进行全方位结构化描述与解析，覆盖音频基础属性、核心内容、说话人信息、环境声音事件、背景音乐等多维度内容。广泛应用于媒资智能编目、内容合规审核前置打标等业务场景。

下面是简单示例代码

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "doubao-seed-2-0-lite-260428",
    "instructions": "# 角色与目标\n【角色定位】你是一位资深音频描述专家，听觉灵敏、逻辑严谨、有良好的文学创作素养和通感能力，擅长听音频写描述。\n【任务说明】我会给你一段音频，你的任务是完整地听完这段音频，进行深度、全面地分析。你需要精准地识别音频中的每一个声音元素（人声、音效、音乐），分析它的声学特征和叙事作用。然后遵守内容要求和输出格式，生成结构清晰、内容详实、语言生动的音频分析报告。",
    "input": [
      {
        "type": "message",
        "role": "user",
        "content": [
          {
              "type": "input_audio", 
              "audio_url": "https://ark-project.tos-cn-beijing.volces.com/doc_audio/audio_demo_video_caption.m4a"
          },
          {
              "type": "input_text", 
              "text": "请整体描述这段音频，按markdown格式输出。# 内容要求\n### 音频概述\n整体概述 音频的 物理属性（比如时长、音色音量、清晰度），核心内容构成，整体听感；\n### 内容分析(如有)\n概括对话或独白的主要内容发展，总结标题和摘要\n### 说话人信息(如有)\n对音频说话部分进行说话人语音特征分析\n### 声音事件信息\n对音频非言语部分进行音频特征分析\n### 音乐信息\n对音频音乐部分进行音频特征分析"
          }
        ]
      }
    ]
  }'
```


按需替换 Model ID，查询 Model ID 参见 [模型列表](https://www.volcengine.com/docs/82379/1330310)。

回复预览

```Plain
# 音频概述\n这是一段时长约11秒的中文美妆电商种草口播音频，整体清晰度极高，无额外背景杂音干扰，音量平稳适中，核心由带货人声和适配产品调性的背景音构成，整体听感轻快亲和，是典型的短视频美妆产品推广片段。\n# 内容分析\n### 内容标题\n本命面霜安利种草\n### 内容摘要\n带货主播向受众分享自己发掘到的心仪面霜产品，先是描述产品云朵般软糯、一抹就吸收的优秀质地，随后点明该面霜兼具熬夜急救、补水保湿的核心功效，快速完成产品核心优势的输出。\n# 说话人信息\n音频中仅出现一名青年女性带货主播，声线明亮饱满，语气热情富有感染力，带着明显的正向安利情绪，语速适中，表达说服力强，完全贴合美妆类电商推广的说话风格。\n# 声音事件信息\n该音频片段未出现独立的非言语类环境音效，全程人声清晰突出，无多余杂音干扰。\n# 音乐信息\n背景搭配一段轻柔舒缓的纯音乐，以钢琴为核心演奏乐器，旋律流畅平缓，氛围温馨治愈，和护肤产品的舒适调性高度契合，音量控制得当，不会喧宾夺主，起到烘托松弛种草氛围的作用。
```


<span id="3d218684"></span>
## 语音识别（ASR）

可对输入音频进行结构化描述性解析，实时转写为纯文本，或附带时间戳的结构化文本，是各类语音理解任务的基础核心能力。结合业务输出需求，能力可覆盖通用文本转写、时间戳标记、多人区分转写、说话人分离日志等细分应用场景。

<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>



* <div data-tips="true" data-tips-type="tip">共支持 <strong>19 种语种识别</strong>：zh（中文）、en（英语）、yue（粤语）、ar（阿拉伯语）、nl（荷兰语）、vi（越南语）、fr（法语）、de（德语）、id（印尼语）、it（意大利语）、ja（日语）、ko（韩语）、ms（马来语）、pt（葡萄牙语）、ru（俄语）、es（西班牙语）、th（泰语）、tr（土耳其语）、fil（菲律宾语）。</div>


* <div data-tips="true" data-tips-type="tip"><strong>中文方言适配</strong>：支持江淮官话、冀鲁官话、兰银官话、中原官话、四川话、粤语、闽南语、上海话、客家话、晋语方言识别。</div>



<span id="d3656de9"></span>
### 普通ASR

仅输出原始纯转写文本，不含额外格式与冗余信息，结果简洁干净。适用于会议纪要、语音笔记等对文本纯净度要求较高的业务场景。

下面是简单示例代码

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "doubao-seed-2-0-lite-260428",
    "instructions": "You are a highly advanced AI specialized in Automatic Speech Recognition (ASR). Your sole function is to transcribe the audio provided by the user.\nYou must adhere to the following rules STRICTLY:\n1. Your output must contain ONLY the transcribed text from the audio.\n2. Do not include any introductory phrases, explanations, apologies, or any other conversational text. For example, never start your response with \"Here is the transcription:\" or \"The transcribed text is:\".\n3. Do not use any formatting, such as markdown, bolding, or italics.\n4. If the audio is unclear, inaudible, or contains no speech, you must output an empty string.",
    "input": [
      {
        "type": "message",
        "role": "user",
        "content": [
          {
              "type": "input_audio", 
              "audio_url": "https://ark-project.tos-cn-beijing.volces.com/doc_audio/audio_demo_video_caption.m4a"
          },
          {
              "type": "input_text", 
              "text": "这段语音的内容是："
          }
        ]
      }
    ]
  }'
```


按需替换 Model ID，查询 Model ID 参见 [模型列表](https://www.volcengine.com/docs/82379/1330310)。

回复预览

```Plain
挖到本命面霜了质地像云朵一样软糯一抹就吸收熬夜急救补水保湿全搞定
```


<span id="19b28dda"></span>
### 输出时间戳

在音频转写的基础上，为每个字（或每句）附带时间戳信息。根据业务使用场景，可进一步分为两种模式：由模型自主完成音频转写并同步打上时间戳，或基于已有的转写文本，完成时间戳精准对齐。

<span id="57fdac64"></span>
#### 音频转写时间戳

模型输出转写文本的同时，为每个字符同步返回精细化起止时间信息，以秒为单位计量。可满足音频检索、视频字幕打轴、音频片段精准定位等业务需求，高效提升内容检索与编辑处理效率。

下面是简单示例代码

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "doubao-seed-2-0-lite-260428",
    "instructions": "你是一个多语种语音识别专家，能够理解捕捉在语音识别过程中的时序关系。你必须按着用户给定的模板进行输出，避免其他无关的输出内容。",
    "input": [
      {
        "type": "message",
        "role": "user",
        "content": [
          {    
              "type": "input_audio", 
              "audio_url": "https://ark-project.tos-cn-beijing.volces.com/doc_audio/audio_demo_video_caption.m4a"
          },
          {
              "type": "input_text", 
              "text": "请转录这段音频文件。对于识别出的每一个字请提供其精确的开始时间和结束时间。\n你需要按着一字一行的格式来排列结果，每一行用'';''隔开。每一行的由三部分组成，分别为开始时间、结束时间、转写字符，并且用''-''将它们分割开。要注意开始时间和结束时间的单位为秒，可以精确到小数点后两位。\n可以参考下面的模板：\n{开始时间}-{结束时间}-{转写字符};{开始时间}-{结束时间}-{转写字符};...{开始时间}-{结束时间}-{转写字符};\n注意你只能按着模板输出结果，请勿输出其它无关的信息和内容。"
          }
        ]
      }
    ]
  }'
```


按需替换 Model ID，查询 Model ID 参见 [模型列表](https://www.volcengine.com/docs/82379/1330310)。

回复预览

```Plain
0.03-0.24-挖;0.24-0.45-到;0.45-0.66-本;0.66-0.84-命;0.84-1.02-面;1.02-1.26-霜;1.26-1.61-了;2.64-2.84-质;2.84-2.98-地;2.98-3.15-像;3.15-3.42-云;3.42-3.60-朵;3.60-3.68-一;3.68-3.87-样;3.87-4.07-软;4.07-4.39-糯;4.42-4.59-一;4.59-4.80-抹;4.80-4.92-就;4.92-5.16-吸;5.16-5.54-收;8.16-8.40-熬;8.40-8.64-夜;8.64-8.85-急;8.85-9.15-救;9.18-9.33-补;9.33-9.48-水;9.48-9.69-保;9.69-10.07-湿;10.14-10.47-全;10.47-10.65-搞;10.65-10.91-定;
```


<span id="f45555d5"></span>
#### 字幕对齐时间戳

适用于已具备完整音频文本的场景，如人工校对完成的字幕内容。仅由模型完成文本与音频的时间轴对齐，严格保留原文内容、不做文本修改。适合字幕制作、卡拉 OK 打轴等。

下面是简单示例代码

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "doubao-seed-2-0-lite-260428",
    "instructions": "你拥有对齐语音内容与转写文本的能力，你能深刻理解语音中存在的时序关系，现在需要你按照用户的要求输出用户所需要的识别结果。你必须按照用户给定的模板进行输出，避免其他无关的输出内容。",
    "input": [
      {
        "type": "message",
        "role": "user",
        "content": [
          {
              "type": "input_audio", 
              "audio_url": "https://ark-project.tos-cn-beijing.volces.com/doc_audio/audio_demo_video_caption.m4a"
          },
          {
              "type": "input_text", 
              "text": "听写这段音频，音频对应转写结果为：「挖到本命面霜了质地像云朵一样软糯一抹就吸收熬夜急救补水保湿全搞定」。现在我需要你根据音频的转写结果把音频中的每个字符都对应上它的开始时间和结束时间。要求你不要篡改转写结果，只需要根据音频的转写结果输出对应的时间信息。\n你需要按着一字一行的格式来排列结果，每一行用'';''隔开。每一行的由三部分组成，分别为开始时间、结束时间、转写字符，并且用''-''将它们分割开。要注意开始时间和结束时间的单位为秒，可以精确到小数点后两位。\n可以参考下面的模板：\n{开始时间}-{结束时间}-{转写字符};...;{开始时间}-{结束时间}-{转写字符};\n注意你只能按着模板输出结果，请勿输出其它无关的信息和内容。"
          }
        ]
      }
    ]
  }'
```


按需替换 Model ID，查询 Model ID 参见 [模型列表](https://www.volcengine.com/docs/82379/1330310)。

回复预览

```Plain
0.03-0.24-挖;0.24-0.45-到;0.45-0.65-本;0.65-0.84-命;0.84-1.02-面;1.02-1.25-霜;1.25-1.58-了;2.65-2.85-质;2.85-2.98-地;2.98-3.15-像;3.15-3.42-云;3.42-3.62-朵;3.62-3.72-一;3.72-3.87-样;3.87-4.05-软;4.05-4.38-糯;4.41-4.59-一;4.59-4.80-抹;4.80-4.92-就;4.92-5.14-吸;5.14-5.52-收;7.98-8.25-熬;8.25-8.46-夜;8.46-8.67-急;8.67-8.99-救;9.02-9.15-补;9.15-9.33-水;9.33-9.51-保;9.51-9.93-湿;9.96-10.31-全;10.31-10.50-搞;10.50-10.77-定;
```


<span id="2220557c"></span>
## 多说话人语音识别（Multispeaker ASR）

支持多人对话音频转写，区分不同发言主体，并为每段内容标注独立说话人编号（`spk0`、`spk1` 等）。适用于访谈交流、日常对话、客服录音等场景，便于内容整理与分类归纳。

下面是简单示例代码

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "doubao-seed-2-0-lite-260428",
    "instructions": "下面是一段多人说话的语音，你需要识别说话内容并标记每句话对应的说话人。对话中出现的第一个人用[spk0]表示，第二个人用[spk1]表示，以此类推。",
    "input": [
      {
        "type": "message",
        "role": "user",
        "content": [
          {
              "type": "input_audio", 
              "audio_url": "https://ark-project.tos-cn-beijing.volces.com/doc_audio/audio_demo_video_multispeaker_01.m4a"
          },
          {
              "type": "input_text", 
              "text": "请顺序输出说话人编号以及语音内容："
          }
        ]
      }
    ]
  }'
```


按需替换 Model ID，查询 Model ID 参见 [模型列表](https://www.volcengine.com/docs/82379/1330310)。

回复预览

```Plain
[spk1]而且还把账号跟它连上，你看，排版没错吧？\n[spk0]哎呦，这排版挺像回事儿啊，没毛病啊，我我打开公众号都这样。\n[spk1]你看，就是这个数据的。\n[spk0]这个图表正好是跟这个内容匹配上的。\n[spk1]没错，对，说的是价格走势，底下放的就是价格走势。\n[spk0]哎呦。\n[spk1]然后哎，然后怎么怎么。
```


<span id="d39e5b2e"></span>
## 说话人日志（Speaker Diarization and ASR）

在多人语音识别能力基础上，进一步为每段发言匹配精准起止时间。统一输出「说话人编号 + 时间范围 + 转录文本」的结构化格式：`[spkN][开始-结束] 说话内容`。

下面是简单示例代码

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "doubao-seed-2-0-lite-260428",
    "instructions": "你是一位顶尖的音频分析专家，能够精准地识别出每一位说话者，并为他们说的话标注精确的时间点。",
    "input": [
      {
        "type": "message",
        "role": "user",
        "content": [
          {
              "type": "input_audio", 
              "audio_url": "https://ark-project.tos-cn-beijing.volces.com/doc_audio/audio_demo_video_multispeaker_01.m4a"
          },
          {
              "type": "input_text", 
              "text": "我有个录音，你帮我整理一下。主要就是把不同人的发言时间都给我找出来，告诉我谁在什么时候说了话。\n你需要按着说话人、时间戳的格式来排列结果。其中时间戳包括开始时间和结束时间，要注意开始时间和结束时间的单位为秒，可以精确到小数点后两位，说话人可以按着出场顺序标记成 spk0、spk1、spk2 等等来代替。\n可以参考下面的模板：\n[说话人][开始时间-结束时间]说话内容[说话人][开始时间-结束时间]说话内容...\n注意你只能按着模板输出结果，请勿输出其它无关的信息和内容。"
          }
        ]
      }
    ]
  }'
```


按需替换 Model ID，查询 Model ID 参见 [模型列表](https://www.volcengine.com/docs/82379/1330310)。

回复预览

```Plain
[spk0][0.00-1.50]哎呀把账号跟他连上你看[spk1][1.54-2.81]排版还挺像回事啊[spk0][2.83-3.32]对吧[spk1][3.44-4.95]没毛病啊我我打开公众号都这样[spk0][5.21-6.44]就是这个数据的[spk1][6.45-7.87]图表正好是跟这个内容[spk0][7.89-8.33]没错[spk1][8.35-8.84]匹配上的[spk0][8.87-11.18]对说的是价格走势底下放的就是价格走势[spk1][11.20-11.55]哎呦[spk0][11.66-12.97]然后哎然后怎么怎么
```


<span id="78796ca8"></span>
## 语音翻译（AST）

对音频口语内容进行跨语言翻译，输出目标语种文本。支持多语种双向互译，可满足国际会议实时同传、多语言视频字幕本地化、出海音频内容审核校对等业务需求。

<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>



* <div data-tips="true" data-tips-type="tip"><strong>语种与互译规则</strong>：AST 共覆盖 <strong>15 个语种</strong>，包含：zh（中文）、en（英语）、yue（粤语）、ar（阿拉伯语）、vi（越南语）、fr（法语）、de（德语）、id（印尼语）、it（意大利语）、ja（日语）、ko（韩语）、pt（葡萄牙语）、ru（俄语）、es（西班牙语）、th（泰语）。仅支持中文、英语与其余 14 个语种双向互译，暂不支持其它语种之间两两互译。</div>


* <div data-tips="true" data-tips-type="tip"><strong>关联能力联动</strong>：结合语音转写（ASR）能力，可提供 <strong>19 个语种</strong>高精度音频转写服务，覆盖语种：zh（中文）、en（英语）、yue（粤语）、ar（阿拉伯语）、nl（荷兰语）、vi（越南语）、fr（法语）、de（德语）、id（印尼语）、it（意大利语）、ja（日语）、ko（韩语）、ms（马来语）、pt（葡萄牙语）、ru（俄语）、es（西班牙语）、th（泰语）、tr（土耳其语）、fil（菲律宾语）。若业务所需翻译语向超出 AST 支持范围，且源语种或目标语种在 ASR 语种列表内，可采用 <strong>ASR 语音转写 + 文本翻译</strong> 组合方案：</div>


   * <div data-tips="true" data-tips-type="tip"><strong>语音转写：</strong>上传原始音频，调用 ASR 能力，将源语言音频精准转写为原文文本。</div>


   * <div data-tips="true" data-tips-type="tip"><strong>文本翻译：</strong>以 ASR 输出的文本作为输入，调用文本翻译能力，生成目标语种译文。</div>



下面是简单示例代码

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "doubao-seed-2-0-lite-260428",
    "instructions": "Your task is to accurately translate the spoken content in the audio and return it in text form.",
    "input": [
      {
        "type": "message",
        "role": "user",
        "content": [
          {
              "type": "input_text", 
              "text": "把这句话翻译成德语，最终输出仅能是翻译结果，不要返回任何其他多余的内容。"
          },
          {
              "type": "input_audio", 
              "audio_url": "https://ark-project.tos-cn-beijing.volces.com/doc_audio/audio_demo_video_caption.m4a"
          }
        ]
      }
    ]
  }'
```


按需替换 Model ID，查询 Model ID 参见 [模型列表](https://www.volcengine.com/docs/82379/1330310)。

回复预览

```Plain
Ich habe endlich meine absolute Traum-Gesichtscreme gefunden! Ihre Textur ist so weich und fluffig wie eine Wolke, sie zieht sofort nach dem Auftragen in die Haut ein. Als perfekte Notlösung nach langen Nächten meistert sie alles mühelos: Sie versorgt die Haut intensiv mit Feuchtigkeit und hält sie langanhaltend feucht.
```


<span id="3fe052be"></span>
## 流式输出

流式输出支持内容动态实时呈现，既能够缓解用户等待焦虑，又可以规避复杂任务因长时间推理引发的客户端超时失败问题，保障请求流程顺畅。

示例代码如下：


<Tabs>
<Tab zoneid="gS3ijRD63V" title="Curl">
<TabTitle>Curl</TabTitle>

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
-H "Authorization: Bearer $ARK_API_KEY" \
-H 'Content-Type: application/json' \
-d '{
    "model": "doubao-seed-2-0-lite-260428",
    "stream": true, 
    "input": [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "audio_url": "https://ark-project.tos-cn-beijing.volces.com/doc_audio/ark_demo_audio.mp3"
                },
                {
                    "type": "input_text",
                    "text": "请识别这段音频内容"
                }
            ]
        }
    ]
}'
```


按需替换 Model ID，查询 Model ID 参见 [模型列表](https://www.volcengine.com/docs/82379/1330310)。


</Tab>
<Tab zoneid="HNErYmonA1" title="Python">
<TabTitle>Python</TabTitle>

```Python
import asyncio
import os
from volcenginesdkarkruntime import AsyncArk
from volcenginesdkarkruntime.types.responses.response_completed_event import ResponseCompletedEvent
from volcenginesdkarkruntime.types.responses.response_reasoning_summary_text_delta_event import ResponseReasoningSummaryTextDeltaEvent
from volcenginesdkarkruntime.types.responses.response_output_item_added_event import ResponseOutputItemAddedEvent
from volcenginesdkarkruntime.types.responses.response_text_delta_event import ResponseTextDeltaEvent
from volcenginesdkarkruntime.types.responses.response_text_done_event import ResponseTextDoneEvent

client = AsyncArk(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=os.getenv('ARK_API_KEY')
)

async def main():
    # Directly use remote audio URL (no need to upload file)
    print("Use remote audio URL for transcription")

    # Streaming Responses API request (matches your curl)
    stream = await client.responses.create(
        model="doubao-seed-2-0-lite-260428",
        input=[
            {"role": "user", "content": [
                {
                    "type": "input_audio",
                    "audio_url": "https://ark-project.tos-cn-beijing.volces.com/doc_audio/ark_demo_audio.mp3"
                },
                {
                    "type": "input_text",
                    "text": "请识别这段音频内容"
                }
            ]},
        ],
        caching={
            "type": "enabled",
        },
        store=True,
        stream=True
    )
    
    # Handle streaming events (same format as your video script)
    async for event in stream:
        if isinstance(event, ResponseReasoningSummaryTextDeltaEvent):
            print(event.delta, end="")
        if isinstance(event, ResponseOutputItemAddedEvent):
            print("\noutPutItem " + event.type + " start:")
        if isinstance(event, ResponseTextDeltaEvent):
            print(event.delta,end="")
        if isinstance(event, ResponseTextDoneEvent):
            print("\noutPutTextDone.")
        if isinstance(event, ResponseCompletedEvent):
            print("Response Completed. Usage = " + event.response.usage.model_dump_json())

if __name__ == "__main__":
    asyncio.run(main())
```



</Tab>
<Tab zoneid="RFBo3ptzIs" title="Go">
<TabTitle>Go</TabTitle>

```Go
package main

import (
        "context"
        "fmt"
        "io"
        "os"

        "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
        "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model/responses"
        "github.com/volcengine/volcengine-go-sdk/volcengine"
)

func main() {
        client := arkruntime.NewClientWithApiKey(
                // Get API Key：https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
                os.Getenv("ARK_API_KEY"),
                arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"),
        )
        ctx := context.Background()

        fmt.Println("----- Use remote audio URL -----")

        inputMessage := &responses.ItemInputMessage{
                Role: responses.MessageRole_user,
                Content: []*responses.ContentItem{
                        {
                                Union: &responses.ContentItem_Audio{
                                        Audio: &responses.ContentItemAudio{
                                                Type:     responses.ContentItemType_input_audio,
                                                AudioUrl: "https://ark-project.tos-cn-beijing.volces.com/doc_audio/ark_demo_audio.mp3",
                                        },
                                },
                        },
                        {
                                Union: &responses.ContentItem_Text{
                                        Text: &responses.ContentItemText{
                                                Type: responses.ContentItemType_input_text,
                                                Text: "请识别这段音频内容",
                                        },
                                },
                        },
                },
        }

        createResponsesReq := &responses.ResponsesRequest{
                Model: "doubao-seed-2-0-lite-260428",
                Input: &responses.ResponsesInput{
                        Union: &responses.ResponsesInput_ListValue{
                                ListValue: &responses.InputItemList{
                                        ListValue: []*responses.InputItem{{
                                                Union: &responses.InputItem_InputMessage{
                                                        InputMessage: inputMessage,
                                                },
                                        }},
                                },
                        },
                },
                Caching: &responses.ResponsesCaching{Type: responses.CacheType_enabled.Enum()},
        }

        resp, err := client.CreateResponsesStream(ctx, createResponsesReq)
        if err != nil {
                fmt.Printf("stream error: %v\n", err)
                return
        }

        var responseId string
        for {
                event, err := resp.Recv()
                if err == io.EOF {
                        break
                }
                if err != nil {
                        fmt.Printf("stream error: %v\n", err)
                        return
                }
                handleEvent(event)
                if responseEvent := event.GetResponse(); responseEvent != nil {
                        responseId = responseEvent.GetResponse().GetId()
                        fmt.Printf("\nResponse ID: %s\n", responseId)
                }
        }

        fmt.Println("\n----- Audio recognition completed -----")
}

func handleEvent(event *responses.Event) {
        switch event.GetEventType() {
        case responses.EventType_response_reasoning_summary_text_delta.String():
                print(event.GetReasoningText().GetDelta())
        case responses.EventType_response_reasoning_summary_text_done.String():
                fmt.Printf("\nAggregated reasoning text: %s\n", event.GetReasoningText().GetText())
        case responses.EventType_response_output_text_delta.String():
                print(event.GetText().GetDelta())
        case responses.EventType_response_output_text_done.String():
                fmt.Printf("\nAggregated output text: %s\n", event.GetTextDone().GetText())
        default:
                return
        }
}
```



</Tab>
<Tab zoneid="YnypdUQWeT" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.ark.example;

import com.volcengine.ark.runtime.service.ArkService;
import com.volcengine.ark.runtime.model.responses.request.*;
import com.volcengine.ark.runtime.model.responses.item.ItemEasyMessage;
import com.volcengine.ark.runtime.model.responses.constant.ResponsesConstants;
import com.volcengine.ark.runtime.model.responses.item.MessageContent;
import com.volcengine.ark.runtime.model.responses.content.InputContentItemAudio;
import com.volcengine.ark.runtime.model.responses.content.InputContentItemText;

import com.volcengine.ark.runtime.model.responses.event.functioncall.FunctionCallArgumentsDoneEvent;
import com.volcengine.ark.runtime.model.responses.event.outputitem.OutputItemAddedEvent;
import com.volcengine.ark.runtime.runtime.model.responses.event.outputitem.OutputItemDoneEvent;
import com.volcengine.ark.runtime.runtime.model.responses.event.outputtext.OutputTextDeltaEvent;
import com.volcengine.ark.runtime.runtime.model.responses.event.outputtext.OutputTextDoneEvent;
import com.volcengine.ark.runtime.runtime.model.responses.event.reasoningsummary.ReasoningSummaryTextDeltaEvent;
import com.volcengine.ark.runtime.runtime.model.responses.event.response.ResponseCompletedEvent;

public class demo {
    public static void main(String[] args) {
        String apiKey = System.getenv("ARK_API_KEY");
        ArkService service = ArkService.builder().apiKey(apiKey).baseUrl("https://ark.cn-beijing.volces.com/api/v3").build();

        System.out.println("===== Use Remote Audio URL Example =====");

        CreateResponsesRequest request = CreateResponsesRequest.builder()
                .model("doubao-seed-2-0-lite-260428")
                .stream(true)
                .input(ResponsesInput.builder().addListItem(
                        ItemEasyMessage.builder().role(ResponsesConstants.MESSAGE_ROLE_USER).content(
                                MessageContent.builder()
                                        .addListItem(InputContentItemAudio.builder()
                                                .audioUrl("https://ark-project.tos-cn-beijing.volces.com/doc_audio/ark_demo_audio.mp3")
                                                .build())
                                        .addListItem(InputContentItemText.builder()
                                                .text("请识别这段音频内容")
                                                .build())
                                        .build()
                        ).build()
                ).build())
                .build();

        service.streamResponse(request)
                .doOnError(Throwable::printStackTrace)
                .blockingForEach(event -> {
                    if (event instanceof ReasoningSummaryTextDeltaEvent) {
                        System.out.print(((ReasoningSummaryTextDeltaEvent) event).getDelta());
                    }
                    if (event instanceof OutputItemAddedEvent) {
                        System.out.println("\nOutputItem " + (((OutputItemAddedEvent) event).getItem().getType()) + " Start: ");
                    }
                    if (event instanceof OutputTextDeltaEvent) {
                        System.out.print(((OutputTextDeltaEvent) event).getDelta());
                    }
                    if (event instanceof OutputTextDoneEvent) {
                        System.out.println("\nOutputText End.");
                    }
                    if (event instanceof OutputItemDoneEvent) {
                        System.out.println("\nOutputItem " + ((OutputItemDoneEvent) event).getItem().getType() + " End.");
                    }
                    if (event instanceof FunctionCallArgumentsDoneEvent) {
                        System.out.println("\nFunctionCall Arguments: " + ((FunctionCallArgumentsDoneEvent) event).getArguments());
                    }
                    if (event instanceof ResponseCompletedEvent) {
                        System.out.println("\nResponse Completed. Usage = " + ((ResponseCompletedEvent) event).getResponse().getUsage());
                    }
                });

        service.shutdownExecutor();
    }
}
```



</Tab>
<Tab zoneid="eHSPi0BvMM" title="OpenAI SDK">
<TabTitle>OpenAI SDK</TabTitle>

```Python
import os
from openai import OpenAI

api_key = os.getenv('ARK_API_KEY')

client = OpenAI(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)

# Directly use remote audio URL (no need to upload file)
print("Use remote audio URL for transcription")

response = client.responses.create(
    model="%audio",
    input=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "audio_url": "https://ark-project.tos-cn-beijing.volces.com/doc_audio/ark_demo_audio.mp3"
                },
                {
                    "type": "input_text",
                    "text": "请识别这段音频内容"
                },
            ]
        }
    ],
    stream=True
)

# Handle streaming events (same format as your video script)
for event in response:
    if event.type == "response.reasoning_summary_text.delta":
        print(event.delta, end="")
    if event.type == "response.output_item.added":
        print("\noutPutItem " + event.type + " start:")
    if event.type == "response.output_text.delta":
        print(event.delta, end="")
    if event.type == "response.output_item.done":
        print("\noutPutTextDone.")
    if event.type == "response.completed":
        print("\nResponse Completed. Usage = " + str(event.response.usage))
```



</Tab>
</Tabs>


<span id="15b40249"></span>
# **使用说明**

<span id="f1499f0b"></span>
## 音频格式说明

支持的音频格式 MIME 类型如下：

**纯音频格式**


* mp3：`audio/mpeg`

* wav：`audio/wav`

* aac：`audio/aac`

* m4a：`audio/mp4`


**视频内嵌音频格式**


* mp3：`audio/mpeg`

* wav：`audio/wav`

* aac：`audio/aac`

* m4a：`audio/mp4`

* pcm：`audio/L16`

* ac3：`audio/ac3`

* alac：`audio/mp4`


<span id="67b61c96"></span>
## 音频 token 用量说明

每秒音频约 6.25 token，实际 token 用量以接口返回的`audio_tokens`为准。

<span id="28510ca2"></span>
## 音频文件容量限制

不同音频输入方式对应的文件大小及时长限制如下：


* Files API 上传（推荐）：单文件大小不超过 512 MB。

* Base64 编码传入：单文件大小不超过 25 MB，音频时长不超过 120 分钟。

* 公网 URL 传入：单文件大小不超过 25 MB，音频时长不超过 120 分钟。




