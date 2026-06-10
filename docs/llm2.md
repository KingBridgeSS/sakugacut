` POST https://ark.cn-beijing.volces.com/api/v3/responses` 

本文介绍 Responses API 创建模型请求时的输入输出参数，供您使用接口时查阅字段含义。


Tips：一键展开折叠，快速检索内容

<div data-tips="true" data-tips-type="default" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="default">打开页面右上角开关后，<strong>ctrl </strong>+ f 可检索页面内所有内容。</div>


<div data-tips="true" data-tips-type="default"><img src="https://portal.volccdn.com/obj/volcfe/cloud-universal-doc/upload_952f1a5ff1c9fc29c4642af62ee3d3ee.png" /></div>




<Tabs>
<Tab zoneid="NxI2ZZeLhf" title="鉴权说明">
<TabTitle>鉴权说明</TabTitle>

本接口支持 API Key /Access Key 鉴权，详见[鉴权认证方式](https://www.volcengine.com/docs/82379/1298459)。


</Tab>
<Tab zoneid="gu5yfTMMdz" title="快速入口">
<TabTitle>快速入口</TabTitle>

<span>![图片](https://portal.volccdn.com/obj/volcfe/cloud-universal-doc/upload_2abecd05ca2779567c6d32f0ddc7874d.png) </span>[模型列表](https://www.volcengine.com/docs/82379/1330310)    <span>![图片](https://portal.volccdn.com/obj/volcfe/cloud-universal-doc/upload_a5fdd3028d35cc512a10bd71b982b6eb.png) </span>[模型计费](https://www.volcengine.com/docs/82379/1544106)     <span>![图片](https://portal.volccdn.com/obj/volcfe/cloud-universal-doc/upload_57d0bca8e0d122ab1191b40101b5df75.png) </span>[Responses API 教程](https://www.volcengine.com/docs/82379/1585128)    <span>![图片](https://portal.volccdn.com/obj/volcfe/cloud-universal-doc/upload_57d0bca8e0d122ab1191b40101b5df75.png) </span>[上下文缓存教程](https://www.volcengine.com/docs/82379/1585128)    <span>![图片](https://portal.volccdn.com/obj/volcfe/cloud-universal-doc/upload_afbcf38bdec05c05089d5de5c3fd8fc8.png) </span>[API Key](https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey?apikey=%7B%7D)


</Tab>
</Tabs>



---



<span id="5Cj9Uxgo"></span>
## Header 参数

Responses API 支持开启数据上报，通过对数据进行统计分析帮助快速排查与定位问题，需要设置的 header 参数见[开启数据上报](https://www.volcengine.com/docs/82379/1544136?lang=zh#d5f5495b)。

<span id="FHypKhIP"></span>
## 请求参数

> 跳转 [响应参数](https://www.volcengine.com/docs/82379/1569618#Qu59cel0)


<span id="pjuiBZGA"></span>
### 请求体


---



**model** `string` <span data-api-tag="require|5YUKhb">必选</span>

您需要调用的模型的 ID （Model ID），[开通模型服务](https://console.volcengine.com/ark/region:ark+cn-beijing/openManagement?LLM=%7B%7D&OpenTokenDrawer=false)，并[查询 Model ID](https://www.volcengine.com/docs/82379/1330310) 。支持的模型请参见 [模型列表](https://www.volcengine.com/docs/82379/1330310?lang=zh)。

当您有多个应用调用模型服务或更细粒度权限管理，可[通过 Endpoint ID 调用模型](https://www.volcengine.com/docs/82379/1099522)。


---



**input**  `string / array` <span data-api-tag="require|zgNDAb">必选</span>

输入的内容，模型需要处理的输入信息。


信息类型


---



**文本输入 ** `string`

输入给模型的文本类型信息，等同于使用 `user` 角色输入的文本信息。


---



**输入的元素列表** `array`

输入给模型的信息元素，可以包括不同的信息类型。


信息类型


---



**输入的消息** `object`

发送给模型的消息，其中角色用于指示指令遵循的优先级层级。由 `developer` 或 `system` 角色给出的指令优先于 `user` 角色给出的指令。`assistant` 角色的消息通常被认为是模型在先前交互中生成的回复。


属性


---



input.**content ** `string / array`  <span data-api-tag="require|LaRVR3">必选</span>

用于生成回复的文本、图片、视频或文件输入，也可以包含先前助手的回复内容。


消息类型


---



**文本输入 ** `string`

输入给模型的文本。


---



**输入的内容列表 ** `array`

包含一个或多个输入项的列表，每个输入项可包含不同类型的内容。


内容类型


---



**输入模型的文本 ** `object`

输入模型的文本。


属性


---



input.content.**text ** `string` ** ** <span data-api-tag="require|nd5oyL">必选</span>

输入模型的文本。


---



input.content.**type ** `string` ** ** <span data-api-tag="require|BEnFka">必选</span>

输入项的类型，此处应为`input_text`。


---



input.content.**translation_options ** `object` ** ** 

特定的翻译模型支持该字段，配置翻译场景下的语种等信息。`source_language`和`target_language`取值参见[支持的语言](https://console.volcengine.com/ark/region:ark+cn-beijing/model/detail?Id=doubao-seed-translation)。

> 支持模型为 doubao\-seed\-translation\-250728 。 



---



属性 \>


---




input.content.**translation_options.** source_language `string`

   需要翻译的信息的源语言语种。



---




input.content.**translation_options.** target_language `string` <span data-api-tag="require|NyEeaK">必选</span>

   需要翻译为何目标语言语种。



---



**输入模型的图片** `object`

输入模型的图片。

图片输入支持**file_id、image_url**两个字段，需二选一传入。多模态理解示例见[图片理解](https://www.volcengine.com/docs/82379/1362931?lang=zh)。


属性


---



input.content.**type ** `string` ** ** <span data-api-tag="require|jmX0U2">必选</span>

输入为图片类型，此处应为`input_image`。


---



input.content.**file_id ** `string` ** ** 

文件ID。


* 文件ID是通过[Files API](https://www.volcengine.com/docs/82379/1870405?lang=zh)上传文件后返回的id。

* **file_id**对应的文件类型需要和**type**保持一致，且文件状态需要为**active**。



---



input.content.**image_url ** `string` ** ** 

要发送给模型的图片 URL。可以是完整的 URL，或以 data URL 形式编码的 base64 图片。


---



input.content.**detail ** `string` ** ** 

取值范围：`low`、`high`、`xhigh`。

理解图片的精细度、不同模型默认取值及对应的具体像素区间，参见[控制图片理解的精细度](https://www.volcengine.com/docs/82379/1362931#bf4d9224)。


---



input.content.**image_pixel_limit  ** `object / null` `默认值 null`

输入给模型的图片的像素范围，如不在此范围，图片会被等比例缩放至该范围。

<div data-tips="true" data-tips-type="warning" data-tips-is-title="true">注意</div>


<div data-tips="true" data-tips-type="warning">图片像素范围需在 [196, 36,000,000]，否则会直接报错。</div>



* 生效优先级：高于 **detail ** 字段，即同时配置 **detail ** 与 **image_pixel_limit ** 字段时，生效 **image_pixel_limit ** 字段配置 **。** 

* 默认生效规则：若未设置**image_pixel_limit**，则使用 **detail ** 配置的值对应的 **min_pixels ** / **max_pixels ** 值。



---



属性 \>


---




input.content.image_pixel_limit.**max_pixels ** `integer`

   传入图片最大像素限制，大于此像素则等比例缩小至 **max_pixels ** 字段取值以下。若未设置，则取值为 **detail ** 配置的值对应的 **max_pixels ** 值。

   * doubao\-seed\-1.8 之前的模型取值范围：(**min_pixels**,  `4014080`]

   * doubao\-seed\-1.8、doubao\-seed\-2.0 模型的取值范围：(**min_pixels**, `9031680`]。



---




input.content.image_pixel_limit.**min_pixels**

   传入图片最小像素限制，小于此像素则等比例放大至 **min_pixels ** 字段取值以上。若未设置，则取值为 **detail ** 配置的值对应的 **min_pixels ** 值。

   * doubao\-seed\-1.8 之前的模型取值范围：[`3136`,  **max_pixels**)

   * doubao\-seed\-1.8、doubao\-seed\-2.0 模型的取值范围：[`1764`,  **max_pixels**)



---



**输入模型的视频** `object`

输入模型的视频。

视频输入支持**file_id、video_url**两个字段，需二选一传入。多模态理解示例见[视频理解](https://www.volcengine.com/docs/82379/1958521?lang=zh#098ef3d4)。


属性


---



input.content.**type ** `string` ** ** <span data-api-tag="require|jmX0U2">必选</span>

输入为视频类型，此处为`input_video`。


---



input.content.**file_id ** `string` ** ** 

文件ID。


* 文件ID是通过[Files API](https://www.volcengine.com/docs/82379/1870405?lang=zh)上传文件后返回的id。

* **file_id**对应的文件类型需要和**type**保持一致，且文件状态需要为**active**。



---



input.content.**video_url ** `string` ** ** 

要发送给模型的视频 URL。可以是完整的 URL，或以 data URL 形式编码的 base64 视频。


---



input.content.**fps** `float`

每秒钟从视频中抽取指定数量的图像，取值范围：`[0.2, 5]`。

如果使用**file_id**参数，**fps**参数则会失效。



---



**输入模型的文件** `object`

输入模型的文件。当前仅支持PDF文件。

文件输入支持**file_id、file_data、file_url**三个字段，需三选一传入。多模态理解示例见[文档理解](https://www.volcengine.com/docs/82379/1958521?lang=zh#18a762a5)。


属性


---



input.content.**type ** `string` ** ** <span data-api-tag="require|jmX0U2">必选</span>

输入为文件类型，此处为`input_file`。


---



input.content.**file_id ** `string` ** ** 

文件ID。


* 文件ID是通过[Files API](https://www.volcengine.com/docs/82379/1870405?lang=zh)上传文件后返回的id。

* **file_id**对应的文件类型需要和**type**保持一致，且文件状态需要为**active**。



---



input.content.**file_data ** `string` ** ** 

文件内容的Base64编码。单个文件大小要求不超过50 MB。


---



input.content.**filename ** `string`

文件名。当使用**file_data**时该参数必填。


---



input.content.**file_url ** `string`

文件的可访问URL。对应文件的大小要求不超过50 MB。





---



**输入模型的音频** `object`

输入模型的音频。

音频输入支持**file_id、audio_url**两个字段，需二选一传入。多模态理解示例见[音频理解](https://www.volcengine.com/docs/82379/2377589?lang=zh)。


属性

input.content.**type ** `string` ** ** <span data-api-tag="require|jmX0U2">必选</span>

输入为音频类型，此处为`input_audio`。


---



input.content.**file_id ** `string` ** ** 

文件ID。


* 文件ID是通过Files API上传文件后返回的id。

* **file_id**对应的文件类型需要和**type**保持一致，且文件状态需要为**active**。



---



input.content.**audio_url ** `string` ** ** 

要发送给模型的音频 URL。可以是完整的 URL，或以 data URL 形式编码的 base64 音频。





---



input.**role ** `string` <span data-api-tag="require|LaRVR3">必选</span>

输入消息的角色，可以是 `user`，`system` ，`assistant`或 `developer`。


---



input.**type ** `string`

消息输入的类型，此处应为`message`。


---



input.**partial ** `boolean`

模型续写模式。

在 **input** 列表里设置最后一条消息的 **role** 为`assistant`，并设置 **partial** 为 `true`开启续写模式，模型会基于 **content** 内容进行续写。在续写模式下，**partial** 为必填项，具体使用见[文档](https://www.volcengine.com/docs/82379/1958520?lang=zh#a1384090)。



---



**上下文元素 ** `object`

表示模型生成回复时需参考的上下文内容。该项可以包含文本、图片和视频输入，以及先前助手的回复和工具调用的输出。


属性


---



**输入的信息**`object`

历史请求中，发给模型的信息。


属性


---



input.**content ** `array` <span data-api-tag="require|M6ZTIE">必选</span>

与 **输入的信息 ** 中 `content` 字段的结构完全一致。


---



input.**role ** `string` <span data-api-tag="require|LaRVR3">必选</span>

输入消息的角色，可选值： `system`，`user` 或 `developer`。


---



input.**type ** `string`

消息输入的类型，此处应为`message`。


---



input.**status ** `string` 

项目状态，可选值：`in_progress`，`completed` 或 `incomplete`。



---



**工具函数信息** `object`

模型调用工具函数的信息


属性


---



input.**arguments ** `string` <span data-api-tag="require|1ANiiU">必选</span>

要传递给函数的参数的 JSON 字符串。


---



input.**call_id ** `string` <span data-api-tag="require|FfESNZ">必选</span>

模型生成的函数工具调用的唯一ID。


---



input.**name ** `string` <span data-api-tag="require|BKQgl5">必选</span>

要运行的函数的名称。


---



input.**type ** `string` <span data-api-tag="require|iIdMyQ">必选</span>

工具调用的类型，始终为 `function_call`。


---



input.**status ** `string`

该项的状态。



---



**工具返回的信息 ** `object`

调用工具后，工具返回的信息


属性


---



input.**call_id** `string` <span data-api-tag="require|pZOgX6">必选</span>

模型生成的函数工具调用的唯一 ID。


---



input.**output ** `string` <span data-api-tag="require|sYBN2y">必选</span>

调用工具后，工具输出的结果。


---



input.**type ** `string` <span data-api-tag="require|5fneD9">必选</span>

工具调用的类型，始终为 `function_call_output`。


---



input.**status ** `string`

该项的状态。




---



**模型思维链信息** `object`

在模型生成响应时使用的思维链信息。如果需要手动管理，需要设置该字段，以便在后续的对话中进行管理。

> 仅模型 `doubao-seed-1.8`、`deepseek-v3.2`、`doubao-seed-2.0`支持设置思维链信息。


<div data-tips="true" data-tips-type="default" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="default">推荐在 Responses API 中使用 previous_response_id，API 将自动保存历史轮次的思考内容，并在多轮交互中回传给模型。</div>



属性


---



input.**id** `string`

思维链信息的唯一标识。


---



input.**type** `string`

输入对象的类型，此处应为 `reasoning`。


---



input.**summary** `array`

思维链内容。


属性


---



input.summary.**text** `string`

思维链内容的文本部分。


---



input.summary.**type** `string`

对象的类型，此处应为`summary_text`。


---



input.**status** `string`

思维链内容的状态。






---



**instructions** `string / null` 

在模型上下文中插入系统消息或者开发者作为第一条指令。当与 **previous_response_id** 一起使用时，前一个回复中的指令不会被继承到下一个回复中。这样可以方便地在新的回复中替换系统（或开发者）消息。

不可与缓存能力一起使用。配置了**instructions** 字段后，本轮请求无法写入缓存和使用缓存，表现为：


* **caching** 字段配置为 `{"type":"enabled"}` 时报错。

* 传入带缓存的 **previous_response_id ** 时，缓存输入（**cached_tokens**）为0。



---



**previous_response_id** `string / null` 

上一个模型回复的唯一标识符。使用该标识符可以实现多轮对话。

<div data-tips="true" data-tips-type="default" data-tips-is-title="true">说明</div>



* <div data-tips="true" data-tips-type="default">在请求中传入 <code>previous_response_id</code>，会引入上一轮请求的输入和回答内容，本次请求的输入tokens 会相应增加。工作原理可参见<a href="https://www.volcengine.com/docs/82379/2123288?lang=zh#41d0a095">多轮对话场景</a>。</div>


* <div data-tips="true" data-tips-type="default">在多轮连续对话中，建议在每次请求之间加入约 100 毫秒的延迟，否则可能会导致调用失败。</div>




---



**expire_at ** `integer` `默认值：创建时刻+259200 `

取值范围：`(创建时刻, 创建时刻+604800]`，即最多保留7天。

设置存储的过期时刻，需传入 UTC Unix 时间戳（单位：秒），对 **store**（上下文存储） 和 **caching**（上下文缓存） 都生效。详细配置及示例代码说明请参见[文档](https://www.volcengine.com/docs/82379/1602228?lang=zh#0387e087)。

注意：缓存存储时间计费，`过期时刻-创建时刻` ，不满 1 小时按 1 小时计算。


---



**max_output_tokens** `integer / null` 

模型输出最大 token 数，包含模型回答和思维链内容。


---



**thinking** `object` `默认值：取决于调用的模型 `

控制模型是否开启深度思考模式。默认开启深度思考模式，可以手动关闭。


属性


---



thinking.**type ** `string`  <span data-api-tag="require|JOQAj6">必选</span>

取值范围：`enabled`， `disabled`，`auto`。


* `enabled`：开启思考模式，模型一定先思考后回答。

* `disabled`：关闭思考模式，模型直接回答问题，不会进行思考。

* `auto`：自动思考模式，模型根据问题自主判断是否需要思考，简单题目直接回答。



---



**reasoning** `object` `默认值 {"effort": "medium"}`

限制深度思考的工作量。减少深度思考工作量可使响应速度更快，并且深度思考的 token 用量更小。


属性


---



reasoning.effort `string`

> 支持该字段的模型、与 **thinking.type** 字段关系见[文档](https://www.volcengine.com/docs/82379/1956279?lang=zh#dc4c1547)。


取值范围：`minimal`，`low`，`medium`，`high`，`max`（仅部分模型支持）。


* `minimal`：关闭思考，直接回答。

* `low`：轻量思考，侧重快速响应。

* `medium`：均衡模式，兼顾速度与深度。

* `high`：深度分析，处理复杂问题。

* `max`：最高程度思考，适配高难度推理任务。该参数仅对指定模型生效，非适配模型传入将不生效。 支持模型列表： 

   * `deepseek-v4-pro-260425`（待支持）

   * `deepseek-v4-flash-260425`（待支持）



---



**include** `array`

指定要在模型响应中返回的其他输出数据，当前支持的取值如下：


* `reasoning.encrypted_content`：经加密及压缩处理后的思考内容原文，支持手动回传该字段，实现思考内容原文的多轮复用。



---



**caching ** `object` `默认值 {"type": "disabled"}`

是否开启缓存，阅读[文档](https://www.volcengine.com/docs/82379/1602228)，了解缓存的具体使用方式。

不可与 **instructions ** 字段、**tools**（除自定义函数 Function Calling 外）字段一起使用。


属性


---



caching.**type ** `string`  <span data-api-tag="require|0SlO8j">必选</span>

取值范围：`enabled`， `disabled`。


* `enabled`：开启缓存。

* `disabled`：关闭缓存。



---



caching.**prefix ** `boolean` `默认值 false`


* true：仅创建公共前缀缓存，模型不回复。

* false：不创建公共前缀缓存。



---



**store** `boolean / null` `默认值 true`

是否储存生成的模型响应，以便后续通过 API 检索。详细上下文管理使用说明，请见[文档](https://www.volcengine.com/docs/82379/1958520?lang=zh#7c5190d3)。


* `false`：不储存，对话内容不能被后续的 API 检索到。

* `true`：储存当前模型响应，对话内容能被后续的 API 检索到。



---



**stream** `boolean / null` `默认值 false`

响应内容是否流式返回。流式输出示例见[文档](https://www.volcengine.com/docs/82379/1958520?lang=zh#641bafe0)。


* `false`：模型生成完所有内容后一次性返回结果。

* `true`：按 SSE 协议逐块返回模型生成内容，并以一条 `data: [DONE]`消息结束。



---



**temperature** `float / null` `默认值 1`

取值范围：` [0, 2]`。

<div data-tips="true" data-tips-type="warning" data-tips-is-title="true">注意</div>


<div data-tips="true" data-tips-type="warning">当调用下列模型，字段取值固定为 <code>1</code>，手动指定的参数值将被忽略。</div>



* <div data-tips="true" data-tips-type="warning"><code>doubao-seed-2-0-pro-260215</code></div>


* <div data-tips="true" data-tips-type="warning"><code>doubao-seed-2-0-lite-260215</code></div>



采样温度。控制了生成文本时对每个候选词的概率分布进行平滑的程度。当取值为 0 时模型仅考虑对数概率最大的一个 token。

较高的值（如 0.8）会使输出更加随机，而较低的值（如 0.2）会使输出更加集中确定。

通常建议仅调整 temperature 或 top_p 其中之一，不建议两者都修改。


---



**top_p** `float / null` `默认值 0.7`

取值范围：` [0, 1]`。

<div data-tips="true" data-tips-type="warning" data-tips-is-title="true">注意</div>


<div data-tips="true" data-tips-type="warning">当调用下列模型，字段取值固定为 <code>0.95</code>，手动指定的参数值将被忽略。</div>



* <div data-tips="true" data-tips-type="warning"><code>doubao-seed-2-0-pro-260215</code></div>


* <div data-tips="true" data-tips-type="warning"><code>doubao-seed-2-0-lite-260215</code></div>


* <div data-tips="true" data-tips-type="warning"><code>doubao-seed-1-8-251228</code></div>



核采样概率阈值。模型会考虑概率质量在 top_p 内的 token 结果。当取值为 0 时模型仅考虑对数概率最大的一个 token。

 0.1 意味着只考虑概率质量最高的前 10% 的 token，取值越大生成的随机性越高，取值越低生成的确定性越高。通常建议仅调整 temperature 或 top_p 其中之一，不建议两者都修改。


---



**text** `object`

模型文本输出的格式定义，可以是自然语言，也可以是结构化的 JSON 数据。详情请看[结构化输出](https://www.volcengine.com/docs/82379/1568221)。


属性


---



text.**format ** `object` `默认值 { "type": "text" }`

指定模型文本输出的格式。


属性


---



**文本格式 ** `object`

响应格式为自然语言。


属性

text.format.**type ** `string` <span data-api-tag="require|blqLhU">必选</span>

回复格式的类型，此处应为 `text`。



---



**JSON Object ** `object` 

响应格式为 JSON 对象。结构化输出示例，见[文档](https://www.volcengine.com/docs/82379/1585128)。

> 该能力尚在 beta 阶段，请谨慎在生产环境使用。



属性


---



text.format.**type ** `string` <span data-api-tag="require|Iylppu">必选</span>

回复格式的类型，此处应为 `json_object`。



---



**JSON Schema  ** `object` 

响应格式为 JSON 对象，遵循schema字段定义的 JSON结构。结构化输出示例，见[文档](https://www.volcengine.com/docs/82379/1585128)。

> 该能力尚在 beta 阶段，请谨慎在生产环境使用。



属性


---



text.format.**type ** `string` <span data-api-tag="require|Iylppu">必选</span>

回复格式的类型，此处应为 `json_schema`。


---



text.format.**name ** `string` <span data-api-tag="require|Iylppu">必选</span>

用户自定义的JSON结构的名称。


---



text.format.**schema ** `object` <span data-api-tag="require|Iylppu">必选</span>

回复格式的JSON格式定义，以JSON Schema对象的形式描述。


---



text.format.**description** `string / null` 

回复用途描述，模型将根据此描述决定如何以该格式回复。


---



text.format.**strict** `boolean / null`  `默认值 false`

是否在生成输出时，启用严格遵循模式。


* true：模型将始终遵循schema字段中定义的格式。

* false：模型将尽可能遵循schema字段中定义的结构。




**tools** `array`

模型可以调用的工具，当您需要让模型调用工具时，需要配置该结构体。


工具类型


---



当前支持多种调用方式，包括


* 内置工具（Built\-in tools）：由方舟提供的预置工具，用以扩展模型内容，如豆包助手、联网搜索工具、图像处理工具、私域知识库搜索工具等。

* MCP工具：通过自定义 MCP 服务器与第三方系统集成。

* 自定义工具（Function Calling）：您自定义的函数，使模型能够使用强类型参数和输出调用您自己的代码，使用示例见 [文档](https://www.volcengine.com/docs/82379/1958524?lang=zh) 。



豆包助手


---



使用豆包助手，快速集成豆包app同款AI能力。详情请参考 [豆包助手文档](https://www.volcengine.com/docs/82379/1978533?lang=zh)。

> 注意：使用前需开通“[豆包助手](https://console.volcengine.com/ark/region:ark+cn-beijing/openManagement)”功能。



---



tools.**type ** `string` `必选`

工具类型，此处填写工具名称，应为`doubao_app`。


---



tools.**feature** ** ** `object` 

豆包助手子功能。


tools.feature.**chat ** `object`

日常沟通功能，豆包同款自由对话，默认关闭。


tools.feature.chat.**type ** `string` `默认值disabled`

取值范围：`enabled`， `disabled`。


* `enabled`：开启此功能。

* `disabled`：关闭此功能。



tools.feature.chat.**role_description ** `string` `默认值：你的名字是豆包,有很强的专业性。`

使用豆包助手时修改角色设定。

此字段与system prompt、instructions 互斥。




tools.feature.**deep_chat ** `object`

深度沟通功能，豆包同款深度思考对话，默认关闭。


tools.feature.deep_chat.**type ** `string` `默认值disabled`

取值范围：`enabled`， `disabled`。


* `enabled`：开启此功能。

* `disabled`：关闭此功能。



tools.feature.deep_chat.**role_description ** `string` `默认值：你的名字是豆包,有很强的专业性。`

使用豆包助手时修改角色设定。

此字段与system prompt、instructions 互斥。






tools.feature.**ai_search ** `object`

联网搜索功能，豆包同款AI搜索能力，默认关闭。


tools.feature.ai_search.**type ** `string` `默认值 disabled`

取值范围：`enabled`， `disabled`。


* `enabled`：开启此功能。

* `disabled`：关闭此功能。



tools.feature.ai_search.**role_description ** `string` `默认值：你的名字是豆包,有很强的专业性。`

使用豆包助手时修改角色设定。

此字段与system prompt、instructions 互斥。




tools.feature.**reasoning_search ** `object`

边想边搜功能，豆包同款结合思考过程的智能搜索能力，默认关闭。


tools.feature.reasoning_search.**type ** `string` `默认值 disabled`

取值范围：`enabled`， `disabled`。


* `enabled`：开启此功能。

* `disabled`：关闭此功能。



tools.feature.reasoning_search.**role_description ** `string` `默认值：你的名字是豆包,有很强的专业性。`

使用豆包助手时修改角色设定。

此字段与system prompt、instructions 互斥。




---



tools.**user_location ** `object` `默认值{"type": "approximate"}`

用户地理位置，用于优化对话与搜索结果，包含 type、country、city、region 字段。示例如下：

```JSON
"user_location":{
     "type":"approximate",
     "country": "中国",
     "region":"浙江",
     "city":"杭州"
}
```


> 注意：填写 type 后，country、city、region 中 至少1个字段有有效值。



函数调用


---



tools.**type ** `string` `必选`

工具类型，此处应为 `function`。


---



tools.**name ** `string` <span data-api-tag="require|pCE4yy">必选</span>

调用的函数的名称。


---



tools.**description ** `string`

调用函数的描述，大模型会用它来判断是否调用这个函数。


---



tools.**parameters ** `object` <span data-api-tag="require|HGLmYt">必选</span>

函数请求参数，以 JSON Schema 格式描述。具体格式请参考 [JSON Schema](https://json-schema.org/understanding-json-schema) 文档，格式如下：

```JSON
{
  "type": "object",
  "properties": {
    "参数名": {
      "type": "string | number | boolean | object | array",
      "description": "参数说明"
    }
  },
  "required": ["必填参数"]
}
```


其中，


* 所有字段名大小写敏感。

* **parameters** 须是合规的 JSON Schema 对象。

* 建议用英文字段名，中文置于 **description** 字段中。



---



tools.**strict** ** ** `boolean` <span data-api-tag="require|HGLmYt">必选</span>`默认值 true`

是否强制执行严格的参数验证。默认为`true`。



联网搜索工具

在互联网上搜索与该提示相关的资源，详情请参考 [Web Search 基础联网搜索](https://www.volcengine.com/docs/82379/1756990)。

> 注意：使用前需开通“[联网内容插件](https://console.volcengine.com/ark/region:ark+cn-beijing/components?action=%7B%7D)”组件。



---



tools.**type ** `string` `必选`

工具类型，此处填写工具名称，应为`web_search`。


---



tools.**sources ** `string[]` 

选择联网搜索的附加内容源。可选头条图文、抖音百科、墨迹天气。


* `toutiao` ：联网搜索的附加头条图文内容源。

* `douyin` ：联网搜索的附加抖音百科内容源。

* `moji` ：联网搜索的附加墨迹天气内容源。



---



tools.**limit ** `integer` `默认值 10`

取值范围：` [1, 50]`。

单轮搜索最大召回条数。

> 说明：影响输入规模与性能，单次搜索最多返回20条结果（单轮可能有多次搜索），默认召回10条。



---



tools.**user_location ** `object` `默认值{"type": "approximate"}`

用户地理位置，用于天气查询等场景，包含 type、country、city、region 字段。示例如下：

```JSON
"user_location":{
     "type":"approximate",
     "country": "中国",
     "region":"浙江",
     "city":"杭州"
}
```


> 注意：填写 type 后，country、city、region 中 至少1个字段有有效值。



---



tools.**max_keyword ** `integer`  

取值范围： `[1, 50]`。

工具一轮使用，最大并行搜索关键词的数量。

> 举例：如模型判断需要搜索关键词：“大模型最新进展”，“2025年科技创新”，“火山方舟进展”。

> 此时max_keyword = 1，则实际仅搜索第一个关键词“大模型最新进展”。



图像处理工具

使用画点、画线、旋转、缩放、框选/裁剪关键区域等基础图像处理工具，详情请参考 [Image Process 图像处理工具](https://www.volcengine.com/docs/82379/1798161)。


---



tools.**type ** `string` `必选`

工具类型，此处填写工具名称，应为`image_process`。


---



tools.**point ** `object`

画点/连线功能开关，控制是否启用点绘制与连线功能。


属性

tools.point.**type ** `string`  `默认值 enabled`

取值范围：`enabled`， `disabled`。


* `enabled`：开启此功能。

* `disabled`：关闭此功能。



---



tools.**grounding ** `object`

框选/裁剪功能开关，控制是否启用关键区域框选或裁剪。


属性

tools.grounding.**type ** `string`  `默认值 enabled`

取值范围：`enabled`， `disabled`。


* `enabled`：开启此功能。

* `disabled`：关闭此功能。



---



tools.**zoom ** `object`

缩放功能开关，控制是否启用全图/指定区域缩放（支持0.5\-2.0倍）。


属性

tools.zoom.**type ** `string`  `默认值 enabled`

取值范围：`enabled`， `disabled`。


* `enabled`：开启此功能。

* `disabled`：关闭此功能。


tools.**rotate ** `object`

旋转功能开关，控制是否启用顺时针旋转（支持0\-359度）。


属性

tools.rotate.**type ** `string`  `默认值 enabled`

取值范围：`enabled`， `disabled`。


* `enabled`：开启此功能。

* `disabled`：关闭此功能。




MCP 工具


---



tools.**type ** `string` `必选`

工具类型，此处填写工具名称，应为`mcp`。


---



tools.**server_label ** `string` `必选`

MCP Server标签，建议设定与工具用途/Server名称一致。


---



tools.**server_url** `string` `必选`

MCP Server访问地址。


---



tools.**headers** `object`

要发送至 MCP 服务器的可选 HTTP 请求头，用于身份验证或其他用途。包含：


* `Authorization` 鉴权信息（不存储）。

* 自定义key\-value。



---



tools.**require_approval** `object/string`  `默认值 always`

指定哪些 MCP 服务器工具需要授权。


属性

**工具批准设置** `string` 

取值范围：


* `always`：所有工具需用户确认后调用。

* `never`：所有工具无需确认，直接调用（可能存在安全风险）。



---



**工具批准筛选** `object` 

指定 MCP 服务器的哪些工具需要审批。可以是 always、never或与需要审批的工具关联的过滤器对象。


属性

tools.require_approval.**always ** `object`

指定哪些工具需要用户确认批准。


属性

tools.require_approval.always **.tool_names ** `array`

需要用户确认批准的工具名称列表。



---



tools.require_approval.**never ** `object`

指定哪些工具不需要用户确认批准使用。


属性

tools.require_approval.never **.tool_names ** `array`

不需要用户确认批准的工具名称列表。





---



tools.**allowed_tools** `array/object`

工具加载范围，默认包含当前MCP Server所有工具。


**属性**

**工具加载范围 ** `array`

允许加载的工具名称的字符串数组。


---



**工具筛选** `object`

指定 MCP 服务器的哪些工具允许使用。


属性

tools.allowed_tools.**tool_names ** `array`

允许的工具名称列表。





私域知识库搜索工具

tools.**type ** `string` `必选`

工具类型，此处填写工具名称，应为`knowledge_search`。


---



tools.**knowledge_resource_id**  ** ** `string` `必选`

填写需使用的私域知识库ID。


---



tools.**limit ** `integer` `默认值 10`

取值范围：` [1, 200]`。

最大可被采用的搜索结果。


---



tools.**max_keyword ** `integer`  

取值范围： `[1, 50]`。

工具一轮使用，最大并行搜索关键词的数量。

> 举例：如模型判断需要搜索关键词：“大模型最新进展”，“2025年科技创新”，“火山方舟进展”。

> 此时max_keyword = 1，则实际仅搜索第一个关键词“大模型最新进展”。



---



tools.**doc_filter**  ** ** `object`

设置文档字段级别的检索过滤条件，确保只在符合条件的文档中检索。


* 支持用作过滤条件的文档字段包括：

   * 系统字段：

      * `doc_id`（仅适用于手动创建的知识库）

      * `_sys_auto_doc_id`（适用于手动创建的知识库和 API 创建的知识库）

   * 自定义字段：

      * 已为知识库文档添加的**文档标签（** 对应知识库 `index_config` 的 `fields` 字段中的 `field`）

* 支持单一条件过滤和多条件组合过滤（支持`And`和`Or`逻辑运算）。详细使用方式和支持字段参见 [filter 表达式](https://www.volcengine.com/docs/84313/1419289#filter-%E8%A1%A8%E8%BE%BE%E5%BC%8F)。


<div data-tips="true" data-tips-type="default" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="default">若自定义字段的类型为<code>Boolean</code>，则它的默认取值范围是 <code>True</code>/<code>False</code>，但大小写规则有所不同：在 cURL 中必须写作 <code>true</code>/<code>false</code>，在 Python 中必须写作 <code>True</code>/<code>False</code>。</div>


单一条件过滤示例（在所给的 doc_id 范围内检索）：

```JSON
"doc_filter": {
    "op": "must", // Query scope operators: must/must_not/range/range_out
    "field": "doc_id",
    "conds": [
        "_sys_auto_gen_doc_id-********01",
        "_sys_auto_gen_doc_id-********02",
        "_sys_auto_gen_doc_id-********03"
    ]
}
```


多条件组合过滤示例（在所给的自定义地域和 doc_id 范围内检索）：

```JSON
"doc_filter": {
    "op": "and", // Logical operators: and/or
    "conds": [   // Condition list. At least one condition is required.
        {
            "op": "must",
            "field": "region",
            "conds": [
                "cn",
                "sg"
            ]
        },
        {
            "op": "must",
            "field": "doc_id",
            "conds": [
                "_sys_auto_gen_doc_id-********01",
                "_sys_auto_gen_doc_id-********02",
                "_sys_auto_gen_doc_id-********03"
            ]
        }
    ]
}
```



---



tools.**description**  ** ** `string`

私域知识库的描述信息。


---



tools.**dense_weight**  ** ** `float`  `默认值 0.5`

取值范围：` [0.2, 1]`。

稠密向量的权重。


* 1 表示纯稠密检索 ，趋向于 0 表示纯字面检索。

* 只有在请求的知识库使用的是混合检索时有效，即索引算法为 hnsw_hybrid。



---



tools.**ranking_options**  ** ** `object` 

检索后处理选项。可参考 [知识库API文档](https://www.volcengine.com/docs/84313/1350012) **post_processing** 字段。


属性

tools.ranking_options.**rerank_switch ** `bool` `默认值 false`

是否自动对检索结果做 rerank。

若设置为true，则会自动请求 rerank 模型排序。


---



tools.ranking_options.**retrieve_count ** `integer` `默认值 25`

进入重排的切片数量。此项只有在 **rerank_switch** 为 **true** 时生效。

注意：retrieve_count 需要大于等于 limit，否则会抛出错误。


---



tools.ranking_options.**get_attachment_link ** `bool` `默认值 false`

是否获取切片中图片的临时下载链接。


---



tools.ranking_options.**chunk_diffusion_count ** `integer` `默认值 0`

取值范围 `[0, 5]`

检索阶段返回命中切片的上下几片邻近切片。默认为 0，表示不进行 chunk diffusion。


---



tools.ranking_options.**chunk_group ** `bool` `默认值 false`

文本聚合。

默认不聚合，对于非结构化文件，考虑到原始文档内容语序对大模型的理解，可开启文本聚合。开启后，会根据文档及文档顺序，对切片进行重新聚合排序返回。


---



tools.ranking_options.**rerank_model ** `string`   `默认值 "base-multilingual-rerank" `

rerank 模型选择。仅在 **rerank_switch ** 为 `True` 的时候生效。

可选模型： 


* （推荐）"`base-multilingual-rerank`"：速度快、长文本、支持70+种语言。

* "`m3-v2-rerank`"：常规文本、支持100+种语言。



---



tools.ranking_options.**rerank_only_chunk ** `bool` `默认值 false`

是否仅根据 chunk 内容计算重排分数。可选值： 


* `True`：只根据 chunk 内容计算分 

* `False`：根据 chunk title + 内容 一起计算排序分




**tool_choice** `string / object`

> 仅 Doubao Seed 1.8 和 Doubao Seed 2.0 系列模型支持此字段。


本次请求，模型返回信息中是否有待调用的工具。

当没有指定工具时，`none` 是默认值。如果存在工具，则 `auto` 是默认值。


可选类型


---



**工具选择模式** `string`

控制模型返回是否包含待调用的工具。


* `none` ：模型返回信息中不可含有待调用的工具。

* `required` ：模型返回信息中必须含待调用的工具。选择此项时请确认存在适合的工具，以减少模型产生幻觉的情况。

* `auto` ：模型自行判断返回信息是否有待调用的工具。



---



**工具调用** `object`

指定待调用工具的范围。模型返回信息中，只允许包含以下模型信息。选择此项时请确认该工具适合用户需求，以减少模型产生幻觉的情况。


属性


---



tool_choice.**type** `string` <span data-api-tag="require|UIUjvD">必选</span>

调用的类型。


* 如果为自定义Function此处应为 `function`，此时 tool_choice.**name** 字段为必选。

* 如果为内置工具，此处填写工具名称，请参考 [Responses API 内置工具](https://www.volcengine.com/docs/82379/1756989)。



---



tool_choice.**name** `string` 

待调用工具的名称。

如果 tool_choice.**type ** 为 `function`，此项为必选。



**max_tool_calls  ** `integer`  

取值范围： `[1, 10]`。

最大工具调用轮次（一轮里不限制次数）。在工具调用达到此限制次数后，提示模型停止更多工具调用并进行回答。

注意：该参数为尽力而为（best effort）机制，不保证成功，最终调用次数会受模型推理效果、工具返回结果有效性等因素影响。


> * 豆包助手不支持此参数。

> * Web Search 基础联网搜索工具的默认值 `3`。

> * Image Process 图像处理工具的默认值 `10`，不支持修改。

> * Knowledge Search 私域知识库搜索工具的默认值为`3`。


**context_management  ** `object`  

上下文管理策略，帮助模型有效利用上下文窗口。


属性


---



context_management **.edits** ** ** `array`

支持的上下文编辑策略，用于管理上下文中思考块和工具调用内容。


策略类型


---



**思考块清除 ** `object`

在开启思考时管理思维链内容。


属性


---



context_management.edits.**type ** `string`

上下文编辑策略类型，此处应为`clear_thinking`。


---



context_management.edits.**keep ** `object/string`

思维链保留策略。


类型


---



**保留最近 N 轮思维链** `object`


属性

context_management.edits.keep.**type ** `string`

思维链保留策略类型，此处应为`thinking_turns`。


---



context_management.edits.keep.**value ** `integer` `默认值 1`

保留最近 N 轮的思维链。



---



**保留所有思维链** `string`

保留所有思维链，此处应为 `all`。




---



**工具调用内容清除** `object`

在对话上下文增长超过配置的阈值时清除工具调用内容。


属性


---



context_management.edits.**type ** `string`

上下文编辑策略类型，此处应为`clear_tool_uses`。


---



context_management.edits.**keep ** `object`

工具调用内容保留策略。


属性


---



context_management.edits.keep.**type ** `string`

工具调用内容保留策略类型，此处应为`tool_uses`。


---



context_management.edits.keep.**value ** `integer` `默认值 3 `

保留最近 N 轮工具调用内容。



---



context_management.edits.**exclude_tools ** `array`

不会被清除的工具名称列表，用于保留重要上下文。


---



context_management.edits.**clear_tool_input ** `boolean` `默认值 false`

是否清除工具调用参数。


---



context_management.edits.**trigger ** `object`

触发工具调用内容清除策略的阈值。


属性


---



context_management.edits.trigger.**type ** `string`

触发工具调用内容清除策略类型，此处应为`tool_uses`。


---



context_management.edits.trigger.**value ** `integer` 

工具调用达到 N 轮时触发清除策略。





<span id="Qu59cel0"></span>
## 响应参数

> 跳转 [请求参数](https://www.volcengine.com/docs/82379/1569618#FHypKhIP)


<span id="fT1TMaZk"></span>
### 非流式调用返回

返回一个 [response object](https://www.volcengine.com/docs/82379/1783703)。

<span id="V8HaFivd"></span>
### 流式调用返回

服务器会在生成 Response 的过程中，通过 Server\-Sent Events（SSE）实时向客户端推送事件。具体事件介绍请参见 [流式响应](https://www.volcengine.com/docs/82379/1599499)。

&nbsp;



