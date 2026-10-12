> [!NOTE]
> This translation describes the upstream aws-samples project and is not updated with this fork. See the [English README](../README.md) for current models, defaults (self sign-up is disabled by default) and deployment options.

<h1 align="center">Bedrock Chat (BrChat)</h1>

<p align="center">
  <img src="https://img.shields.io/github/v/release/aws-samples/bedrock-chat?style=flat-square" />
  <img src="https://img.shields.io/github/license/aws-samples/bedrock-chat?style=flat-square" />
  <img src="https://img.shields.io/github/actions/workflow/status/aws-samples/bedrock-chat/cdk.yml?style=flat-square" />
  <a href="https://github.com/aws-samples/bedrock-chat/issues?q=is%3Aissue%20state%3Aopen%20label%3Aroadmap">
    <img src="https://img.shields.io/badge/roadmap-view-blue?style=flat-square" />
  </a>
</p>

[English](https://github.com/aws-samples/bedrock-chat/blob/v3/README.md) | [日本語](https://github.com/aws-samples/bedrock-chat/blob/v3/docs/README_ja-JP.md) | [한국어](https://github.com/aws-samples/bedrock-chat/blob/v3/docs/README_ko-KR.md) | [中文](https://github.com/aws-samples/bedrock-chat/blob/v3/docs/README_zh-CN.md) | [Français](https://github.com/aws-samples/bedrock-chat/blob/v3/docs/README_fr-FR.md) | [Deutsch](https://github.com/aws-samples/bedrock-chat/blob/v3/docs/README_de-DE.md) | [Español](https://github.com/aws-samples/bedrock-chat/blob/v3/docs/README_es-ES.md) | [Italian](https://github.com/aws-samples/bedrock-chat/blob/v3/docs/README_it-IT.md) | [Norsk](https://github.com/aws-samples/bedrock-chat/blob/v3/docs/README_nb-NO.md) | [ไทย](https://github.com/aws-samples/bedrock-chat/blob/v3/docs/README_th-TH.md) | [Bahasa Indonesia](https://github.com/aws-samples/bedrock-chat/blob/v3/docs/README_id-ID.md) | [Bahasa Melayu](https://github.com/aws-samples/bedrock-chat/blob/v3/docs/README_ms-MY.md) | [Tiếng Việt](https://github.com/aws-samples/bedrock-chat/blob/v3/docs/README_vi-VN.md) | [Polski](https://github.com/aws-samples/bedrock-chat/blob/v3/docs/README_pl-PL.md) | [Português Brasil](https://github.com/aws-samples/bedrock-chat/blob/v3/docs/README_pt-BR.md)


แพลตฟอร์ม AI สร้างเนื้อหาหลายภาษาที่ขับเคลื่อนโดย [Amazon Bedrock](https://aws.amazon.com/bedrock/)
รองรับการแชท บอทที่กำหนดเองพร้อมความรู้ (RAG) การแบ่งปันบอทผ่านร้านค้าบอท และการทำงานอัตโนมัติโดยใช้เอเจนต์

![](./imgs/demo.gif)

> [!Warning]
>
> **เวอร์ชัน V3 ได้เปิดตัวแล้ว โปรดอ่าน [คู่มือการย้าย](./migration/V2_TO_V3_th-TH.md) อย่างละเอียดเพื่ออัปเดต** หากไม่ระมัดระวัง **บอทจากเวอร์ชัน V2 จะไม่สามารถใช้งานได้**

### การปรับแต่งบอท / ร้านค้าบอท

เพิ่มคำแนะนำและความรู้ของคุณเอง (หรือที่เรียกว่า [RAG](https://aws.amazon.com/what-is/retrieval-augmented-generation/)) บอทสามารถแบ่งปันระหว่างผู้ใช้แอปพลิเคชันผ่านตลาดร้านค้าบอท บอทที่ปรับแต่งแล้วยังสามารถเผยแพร่เป็น API แบบสแตนด์อโลนได้ (ดู[รายละเอียด](./PUBLISH_API_th-TH.md))

<details>
<summary>ภาพหน้าจอ</summary>

![](./imgs/customized_bot_creation.png)
![](./imgs/fine_grained_permission.png)
![](./imgs/bot_store.png)
![](./imgs/bot_api_publish_screenshot3.png)

คุณยังสามารถนำเข้า [Amazon Bedrock's KnowledgeBase](https://aws.amazon.com/bedrock/knowledge-bases/) ที่มีอยู่แล้วได้

![](./imgs/import_existing_kb.png)

</details>

> [!Important]
> เพื่อเหตุผลด้านการกำกับดูแล เฉพาะผู้ใช้ที่ได้รับอนุญาตเท่านั้นที่สามารถสร้างบอทที่กำหนดเองได้ เพื่อให้สามารถสร้างบอทที่กำหนดเองได้ ผู้ใช้ต้องเป็นสมาชิกของกลุ่มที่เรียกว่า `CreatingBotAllowed` ซึ่งสามารถตั้งค่าได้ผ่านคอนโซลการจัดการ > Amazon Cognito User pools หรือ aws cli โปรดทราบว่าสามารถอ้างอิง user pool id ได้โดยเข้าถึง CloudFormation > BedrockChatStack > Outputs > `AuthUserPoolIdxxxx`

### คุณสมบัติการจัดการ

การจัดการ API การทำเครื่องหมายบอทว่าจำเป็น วิเคราะห์การใช้งานสำหรับบอท [รายละเอียด](./ADMINISTRATOR_th-TH.md)

<details>
<summary>ภาพหน้าจอ</summary>

![](./imgs/admin_bot_menue.png)
![](./imgs/bot_store.png)
![](./imgs/admn_api_management.png)
![](./imgs/admin_bot_analytics.png))

</details>

### เอเจนต์

โดยใช้[ฟังก์ชันเอเจนต์](./AGENT_th-TH.md) แชทบอทของคุณสามารถจัดการงานที่ซับซ้อนได้โดยอัตโนมัติ ตัวอย่างเช่น เพื่อตอบคำถามของผู้ใช้ เอเจนต์สามารถดึงข้อมูลที่จำเป็นจากเครื่องมือภายนอกหรือแบ่งงานออกเป็นหลายขั้นตอนสำหรับการประมวลผล

<details>
<summary>ภาพหน้าจอ</summary>

![](./imgs/agent1.png)
![](./imgs/agent2.png)

</details>

## 🚀 การติดตั้งแบบง่ายมาก

- ในภูมิภาค us-east-1 เปิด [Bedrock Model access](https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess) > `Manage model access` > เลือกโมเดลทั้งหมดที่คุณต้องการใช้แล้วกด `Save changes`

<details>
<summary>ภาพหน้าจอ</summary>

![](./imgs/model_screenshot.png)

</details>

### ภูมิภาคที่รองรับ

โปรดตรวจสอบให้แน่ใจว่าคุณติดตั้ง Bedrock Chat ในภูมิภาค[ที่มี OpenSearch Serverless และ Ingestion APIs พร้อมใช้งาน](https://docs.aws.amazon.com/general/latest/gr/opensearch-service.html) หากคุณต้องการใช้บอทและสร้างฐานความรู้ (OpenSearch Serverless เป็นตัวเลือกเริ่มต้น) ณ เดือนสิงหาคม 2025 รองรับภูมิภาคต่อไปนี้: us-east-1, us-east-2, us-west-1, us-west-2, ap-south-1, ap-northeast-1, ap-northeast-2, ap-southeast-1, ap-southeast-2, ca-central-1, eu-central-1, eu-west-1, eu-west-2, eu-south-2, eu-north-1, sa-east-1

สำหรับพารามิเตอร์ **bedrock-region** คุณต้องเลือกภูมิภาค[ที่มี Bedrock พร้อมใช้งาน](https://docs.aws.amazon.com/general/latest/gr/bedrock.html)

- เปิด [CloudShell](https://console.aws.amazon.com/cloudshell/home) ในภูมิภาคที่คุณต้องการติดตั้ง
- รันการติดตั้งด้วยคำสั่งต่อไปนี้ หากคุณต้องการระบุเวอร์ชันที่จะติดตั้งหรือต้องการใช้นโยบายความปลอดภัย โปรดระบุพารามิเตอร์ที่เหมาะสมจาก [พารามิเตอร์เสริม](#optional-parameters)

```sh
git clone https://github.com/aws-samples/bedrock-chat.git
cd bedrock-chat
chmod +x bin.sh
./bin.sh
```

- คุณจะถูกถามว่าเป็นผู้ใช้ใหม่หรือใช้ v3 หากคุณไม่ใช่ผู้ใช้ต่อเนื่องจาก v0 โปรดป้อน `y`

### พารามิเตอร์เสริม

คุณสามารถระบุพารามิเตอร์ต่อไปนี้ระหว่างการติดตั้งเพื่อเพิ่มความปลอดภัยและการปรับแต่ง:

- **--disable-self-register**: ปิดการลงทะเบียนด้วยตนเอง (ค่าเริ่มต้น: เปิดใช้งาน) หากตั้งค่านี้ คุณจะต้องสร้างผู้ใช้ทั้งหมดบน cognito และจะไม่อนุญาตให้ผู้ใช้ลงทะเบียนบัญชีด้วยตนเอง
- **--enable-lambda-snapstart**: เปิดใช้งาน [Lambda SnapStart](https://docs.aws.amazon.com/lambda/latest/dg/snapstart.html) (ค่าเริ่มต้น: ปิดใช้งาน) หากตั้งค่านี้ จะช่วยปรับปรุงเวลาเริ่มต้นเย็นของฟังก์ชัน Lambda ให้ตอบสนองได้เร็วขึ้นเพื่อประสบการณ์ผู้ใช้ที่ดีขึ้น
- **--ipv4-ranges**: รายการช่วง IPv4 ที่อนุญาต คั่นด้วยเครื่องหมายจุลภาค (ค่าเริ่มต้น: อนุญาตทุกที่อยู่ ipv4)
- **--ipv6-ranges**: รายการช่วง IPv6 ที่อนุญาต คั่นด้วยเครื่องหมายจุลภาค (ค่าเริ่มต้น: อนุญาตทุกที่อยู่ ipv6)
- **--disable-ipv6**: ปิดการเชื่อมต่อผ่าน IPv6 (ค่าเริ่มต้น: เปิดใช้งาน)
- **--allowed-signup-email-domains**: รายการโดเมนอีเมลที่อนุญาตสำหรับการลงทะเบียน คั่นด้วยเครื่องหมายจุลภาค (ค่าเริ่มต้น: ไม่จำกัดโดเมน)
- **--bedrock-region**: กำหนดภูมิภาคที่มี bedrock พร้อมใช้งาน (ค่าเริ่มต้น: us-east-1)
- **--repo-url**: ที่เก็บที่กำหนดเองของ Bedrock Chat ที่จะติดตั้ง หากมีการ fork หรือใช้การควบคุมซอร์สโค้ดที่กำหนดเอง (ค่าเริ่มต้น: https://github.com/aws-samples/bedrock-chat.git)
- **--version**: เวอร์ชันของ Bedrock Chat ที่จะติดตั้ง (ค่าเริ่มต้น: เวอร์ชันล่าสุดในการพัฒนา)
- **--cdk-json-override**: คุณสามารถแทนที่ค่าบริบท CDK ใดๆ ระหว่างการติดตั้งโดยใช้บล็อก JSON แทนที่ ซึ่งช่วยให้คุณแก้ไขการกำหนดค่าได้โดยไม่ต้องแก้ไขไฟล์ cdk.json โดยตรง

ตัวอย่างการใช้งาน:

```bash
./bin.sh --cdk-json-override '{
  "context": {
    "selfSignUpEnabled": false,
    "enableLambdaSnapStart": true,
    "allowedIpV4AddressRanges": ["192.168.1.0/24"],
    "allowedCountries": ["US", "CA"],
    "allowedSignUpEmailDomains": ["example.com"],
    "globalAvailableModels": [
      "claude-v3.7-sonnet",
      "claude-v3.5-sonnet",
      "amazon-nova-pro",
      "amazon-nova-lite",
      "llama3-3-70b-instruct"
    ]
  }
}'
```

JSON ที่แทนที่ต้องเป็นไปตามโครงสร้างเดียวกับ cdk.json คุณสามารถแทนที่ค่าบริบทใดๆ รวมถึง:

- `selfSignUpEnabled`
- `enableLambdaSnapStart`
- `allowedIpV4AddressRanges`
- `allowedIpV6AddressRanges`
- `allowedCountries`
- `allowedSignUpEmailDomains`
- `bedrockRegion`
- `enableRagReplicas`
- `enableBedrockCrossRegionInference`
- `globalAvailableModels`: รับรายการ ID โมเดลที่จะเปิดใช้งาน ค่าเริ่มต้นคือรายการว่าง ซึ่งจะเปิดใช้งานโมเดลทั้งหมด
- `logoPath`: เส้นทางสัมพัทธ์ไปยังไฟล์โลโก้ในไดเรกทอรี `public/` ของฟรอนต์เอนด์ที่ปรากฏที่ด้านบนของลิ้นชักนำทาง
- และค่าบริบทอื่นๆ ที่กำหนดใน cdk.json

> [!Note]
> ค่าที่แทนที่จะถูกรวมกับการกำหนดค่า cdk.json ที่มีอยู่ในระหว่างการติดตั้งใน AWS code build ค่าที่ระบุในการแทนที่จะมีความสำคัญเหนือกว่าค่าใน cdk.json

#### ตัวอย่างคำสั่งพร้อมพารามิเตอร์:

```sh
./bin.sh --disable-self-register --ipv4-ranges "192.0.2.0/25,192.0.2.128/25" --ipv6-ranges "2001:db8:1:2::/64,2001:db8:1:3::/64" --allowed-signup-email-domains "example.com,anotherexample.com" --bedrock-region "us-west-2" --version "v1.2.6"
```

- หลังจากประมาณ 35 นาที คุณจะได้รับผลลัพธ์ต่อไปนี้ ซึ่งคุณสามารถเข้าถึงได้จากเบราว์เซอร์ของคุณ

```
Frontend URL: https://xxxxxxxxx.cloudfront.net
```

![](./imgs/signin.png)

หน้าจอลงทะเบียนจะปรากฏดังแสดงด้านบน ซึ่งคุณสามารถลงทะเบียนอีเมลและเข้าสู่ระบบได้

> [!Important]
> หากไม่ตั้งค่าพารามิเตอร์เสริม วิธีการติดตั้งนี้จะอนุญาตให้ทุกคนที่รู้ URL สามารถลงทะเบียนได้ สำหรับการใช้งานในการผลิต แนะนำอย่างยิ่งให้เพิ่มข้อจำกัดที่อยู่ IP และปิดการลงทะเบียนด้วยตนเองเพื่อลดความเสี่ยงด้านความปลอดภัย (คุณสามารถกำหนด allowed-signup-email-domains เพื่อจำกัดผู้ใช้ให้เฉพาะที่อยู่อีเมลจากโดเมนของบริษัทคุณเท่านั้นที่สามารถลงทะเบียนได้) ใช้ทั้ง ipv4-ranges และ ipv6-ranges สำหรับข้อจำกัดที่อยู่ IP และปิดการลงทะเบียนด้วยตนเองโดยใช้ disable-self-register เมื่อรัน ./bin

> [!TIP]
> หาก `Frontend URL` ไม่ปรากฏหรือ Bedrock Chat ทำงานไม่ถูกต้อง อาจเป็นปัญหาจากเวอร์ชันล่าสุด ในกรณีนี้ โปรดเพิ่ม `--version "v3.0.0"` ในพารามิเตอร์และลองติดตั้งอีกครั้ง

## สถาปัตยกรรม

เป็นสถาปัตยกรรมที่สร้างขึ้นบนบริการที่จัดการโดย AWS ซึ่งช่วยขจัดความจำเป็นในการจัดการโครงสร้างพื้นฐาน ด้วยการใช้ Amazon Bedrock จึงไม่จำเป็นต้องติดต่อกับ API ภายนอก AWS ทำให้สามารถปรับใช้แอปพลิเคชันที่ขยายขนาดได้ เชื่อถือได้ และปลอดภัย

- [Amazon DynamoDB](https://aws.amazon.com/dynamodb/): ฐานข้อมูล NoSQL สำหรับจัดเก็บประวัติการสนทนา
- [Amazon API Gateway](https://aws.amazon.com/api-gateway/) + [AWS Lambda](https://aws.amazon.com/lambda/): จุดเชื่อมต่อ API แบ็กเอนด์ ([AWS Lambda Web Adapter](https://github.com/awslabs/aws-lambda-web-adapter), [FastAPI](https://fastapi.tiangolo.com/))
- [Amazon CloudFront](https://aws.amazon.com/cloudfront/) + [S3](https://aws.amazon.com/s3/): การส่งมอบแอปพลิเคชันฟรอนต์เอนด์ ([React](https://react.dev/), [Tailwind CSS](https://tailwindcss.com/))
- [AWS WAF](https://aws.amazon.com/waf/): การจำกัดที่อยู่ IP
- [Amazon Cognito](https://aws.amazon.com/cognito/): การยืนยันตัวตนผู้ใช้
- [Amazon Bedrock](https://aws.amazon.com/bedrock/): บริการที่จัดการเพื่อใช้โมเดลพื้นฐานผ่าน API
- [Amazon Bedrock Knowledge Bases](https://aws.amazon.com/bedrock/knowledge-bases/): ให้บริการอินเตอร์เฟซที่จัดการสำหรับ Retrieval-Augmented Generation ([RAG](https://aws.amazon.com/what-is/retrieval-augmented-generation/)) โดยให้บริการสำหรับการฝังและแยกวิเคราะห์เอกสาร
- [Amazon EventBridge Pipes](https://aws.amazon.com/eventbridge/pipes/): รับอีเวนต์จาก DynamoDB stream และเริ่มการทำงานของ Step Functions เพื่อฝังความรู้ภายนอก
- [AWS Step Functions](https://aws.amazon.com/step-functions/): จัดการไปป์ไลน์การนำเข้าเพื่อฝังความรู้ภายนอกลงใน Bedrock Knowledge Bases
- [Amazon OpenSearch Serverless](https://aws.amazon.com/opensearch-service/features/serverless/): ทำหน้าที่เป็นฐานข้อมูลแบ็กเอนด์สำหรับ Bedrock Knowledge Bases โดยให้ความสามารถในการค้นหาแบบเต็มรูปแบบและการค้นหาแบบเวกเตอร์ ช่วยให้สามารถค้นคืนข้อมูลที่เกี่ยวข้องได้อย่างแม่นยำ
- [Amazon Athena](https://aws.amazon.com/athena/): บริการสืบค้นเพื่อวิเคราะห์ S3 bucket

![](./imgs/arch.png)

## การ Deploy โดยใช้ CDK

การ Deploy แบบง่ายใช้ [AWS CodeBuild](https://aws.amazon.com/codebuild/) เพื่อดำเนินการ deploy ด้วย CDK ภายใน ส่วนนี้จะอธิบายขั้นตอนการ deploy โดยตรงด้วย CDK

- กรุณาเตรียม UNIX, Docker และสภาพแวดล้อมรันไทม์ Node.js ให้พร้อม

> [!Important]
> หากพื้นที่เก็บข้อมูลในสภาพแวดล้อมท้องถิ่นไม่เพียงพอระหว่างการ deploy การ bootstrap CDK อาจเกิดข้อผิดพลาด เราแนะนำให้ขยายขนาดโวลุ่มของอินสแตนซ์ก่อนทำการ deploy

- โคลนที่เก็บนี้

```
git clone https://github.com/aws-samples/bedrock-chat
```

- ติดตั้งแพ็คเกจ npm

```
cd bedrock-chat
cd cdk
npm ci
```

- หากจำเป็น ให้แก้ไขรายการต่อไปนี้ใน [cdk.json](./cdk/cdk.json)

  - `bedrockRegion`: ภูมิภาคที่มี Bedrock ให้บริการ **หมายเหตุ: Bedrock ยังไม่รองรับทุกภูมิภาคในขณะนี้**
  - `allowedIpV4AddressRanges`, `allowedIpV6AddressRanges`: ช่วง IP Address ที่อนุญาต
  - `enableLambdaSnapStart`: ค่าเริ่มต้นคือ true ตั้งค่าเป็น false หากกำลัง deploy ไปยัง[ภูมิภาคที่ไม่รองรับ Lambda SnapStart สำหรับฟังก์ชัน Python](https://docs.aws.amazon.com/lambda/latest/dg/snapstart.html#snapstart-supported-regions)
  - `globalAvailableModels`: ค่าเริ่มต้นคือทั้งหมด หากตั้งค่า (รายการ model ID) จะควบคุมโมเดลที่ปรากฏในเมนูแบบเลื่อนลงทั่วทั้งการแชทสำหรับผู้ใช้ทุกคนและระหว่างการสร้างบอทในแอปพลิเคชัน Bedrock Chat
  - `logoPath`: เส้นทางสัมพันธ์ภายใต้ `frontend/public` ที่ชี้ไปยังรูปภาพที่แสดงที่ด้านบนของลิ้นชักแอปพลิเคชัน
รองรับ model ID ต่อไปนี้ (โปรดตรวจสอบว่าได้เปิดใช้งานในคอนโซล Bedrock ภายใต้ Model access ในภูมิภาคที่คุณ deploy):
- **Claude Models:** `claude-v4-opus`, `claude-v4.1-opus`, `claude-v4-sonnet`, `claude-v3.5-sonnet`, `claude-v3.5-sonnet-v2`, `claude-v3.7-sonnet`, `claude-v3.5-haiku`, `claude-v3-haiku`, `claude-v3-opus`
- **Amazon Nova Models:** `amazon-nova-pro`, `amazon-nova-lite`, `amazon-nova-micro`
- **Mistral Models:** `mistral-7b-instruct`, `mixtral-8x7b-instruct`, `mistral-large`, `mistral-large-2`
- **DeepSeek Models:** `deepseek-r1`
- **Meta Llama Models:** `llama3-3-70b-instruct`, `llama3-2-1b-instruct`, `llama3-2-3b-instruct`, `llama3-2-11b-instruct`, `llama3-2-90b-instruct`

รายการทั้งหมดสามารถพบได้ใน [index.ts](./frontend/src/constants/index.ts)

- ก่อนที่จะ deploy CDK คุณจะต้องทำการ Bootstrap หนึ่งครั้งสำหรับภูมิภาคที่คุณจะ deploy

```
npx cdk bootstrap
```

- Deploy โปรเจ็กต์ตัวอย่างนี้

```
npx cdk deploy --require-approval never --all
```

- คุณจะได้รับผลลัพธ์คล้ายกับด้านล่าง URL ของเว็บแอปจะแสดงใน `BedrockChatStack.FrontendURL` โปรดเข้าถึงจากเบราว์เซอร์ของคุณ

```sh
 ✅  BedrockChatStack

✨  Deployment time: 78.57s

Outputs:
BedrockChatStack.AuthUserPoolClientIdXXXXX = xxxxxxx
BedrockChatStack.AuthUserPoolIdXXXXXX = ap-northeast-1_XXXX
BedrockChatStack.BackendApiBackendApiUrlXXXXX = https://xxxxx.execute-api.ap-northeast-1.amazonaws.com
BedrockChatStack.FrontendURL = https://xxxxx.cloudfront.net
```

### การกำหนดพารามิเตอร์

คุณสามารถกำหนดพารามิเตอร์สำหรับการ deploy ได้สองวิธี: ใช้ `cdk.json` หรือใช้ไฟล์ `parameter.ts` ที่มีการตรวจสอบประเภท

#### การใช้ cdk.json (วิธีแบบดั้งเดิม)

วิธีแบบดั้งเดิมในการกำหนดค่าพารามิเตอร์คือการแก้ไขไฟล์ `cdk.json` วิธีนี้ง่ายแต่ขาดการตรวจสอบประเภท:

```json
{
  "app": "npx ts-node --prefer-ts-exts bin/bedrock-chat.ts",
  "context": {
    "bedrockRegion": "us-east-1",
    "allowedIpV4AddressRanges": ["0.0.0.0/1", "128.0.0.0/1"],
    "selfSignUpEnabled": true,
    "globalAvailableModels": [
      "claude-v3.7-sonnet",
      "claude-v3.5-sonnet",
      "amazon-nova-pro",
      "amazon-nova-lite", 
      "llama3-3-70b-instruct"
    ],
  }
}
```

#### การใช้ parameter.ts (วิธีที่แนะนำที่มีการตรวจสอบประเภท)

สำหรับการตรวจสอบประเภทและประสบการณ์นักพัฒนาที่ดีขึ้น คุณสามารถใช้ไฟล์ `parameter.ts` เพื่อกำหนดพารามิเตอร์ของคุณ:

```typescript
// กำหนดพารามิเตอร์สำหรับสภาพแวดล้อมเริ่มต้น
bedrockChatParams.set("default", {
  bedrockRegion: "us-east-1",
  allowedIpV4AddressRanges: ["192.168.0.0/16"],
  selfSignUpEnabled: true,
  globalAvailableModels: [
      "claude-v3.7-sonnet",
      "claude-v3.5-sonnet",
      "amazon-nova-pro",
      "amazon-nova-lite",
      "llama3-3-70b-instruct"
    ],
});

// กำหนดพารามิเตอร์สำหรับสภาพแวดล้อมเพิ่มเติม
bedrockChatParams.set("dev", {
  bedrockRegion: "us-west-2",
  allowedIpV4AddressRanges: ["10.0.0.0/8"],
  enableRagReplicas: false, // ประหยัดต้นทุนสำหรับสภาพแวดล้อมการพัฒนา
  enableBotStoreReplicas: false, // ประหยัดต้นทุนสำหรับสภาพแวดล้อมการพัฒนา
});

bedrockChatParams.set("prod", {
  bedrockRegion: "us-east-1",
  allowedIpV4AddressRanges: ["172.16.0.0/12"],
  enableLambdaSnapStart: true,
  enableRagReplicas: true, // เพิ่มความพร้อมใช้งานสำหรับการผลิต
  enableBotStoreReplicas: true, // เพิ่มความพร้อมใช้งานสำหรับการผลิต
});
```

> [!Note]
> ผู้ใช้ที่มีอยู่สามารถใช้ `cdk.json` ต่อไปได้โดยไม่ต้องเปลี่ยนแปลงใดๆ แนะนำให้ใช้วิธี `parameter.ts` สำหรับการ deploy ใหม่หรือเมื่อคุณต้องจัดการหลายสภาพแวดล้อม

### การ Deploy หลายสภาพแวดล้อม

คุณสามารถ deploy หลายสภาพแวดล้อมจากโค้ดเดียวกันโดยใช้ไฟล์ `parameter.ts` และตัวเลือก `-c envName`

#### ข้อกำหนดเบื้องต้น

1. กำหนดสภาพแวดล้อมของคุณใน `parameter.ts` ตามที่แสดงด้านบน
2. แต่ละสภาพแวดล้อมจะมีทรัพยากรของตัวเองพร้อมคำนำหน้าเฉพาะสภาพแวดล้อม

#### คำสั่ง Deploy

เพื่อ deploy สภาพแวดล้อมเฉพาะ:

```bash
# Deploy สภาพแวดล้อมการพัฒนา
npx cdk deploy --all -c envName=dev

# Deploy สภาพแวดล้อมการผลิต
npx cdk deploy --all -c envName=prod
```

หากไม่ได้ระบุสภาพแวดล้อม จะใช้สภาพแวดล้อม "default":

```bash
# Deploy สภาพแวดล้อมเริ่มต้น
npx cdk deploy --all
```

#### หมายเหตุสำคัญ

1. **การตั้งชื่อสแต็ก**:

   - สแต็กหลักสำหรับแต่ละสภาพแวดล้อมจะมีคำนำหน้าด้วยชื่อสภาพแวดล้อม (เช่น `dev-BedrockChatStack`, `prod-BedrockChatStack`)
   - อย่างไรก็ตาม สแต็กบอทที่กำหนดเอง (`BrChatKbStack*`) และสแต็กการเผยแพร่ API (`ApiPublishmentStack*`) ไม่ได้รับคำนำหน้าสภาพแวดล้อมเนื่องจากถูกสร้างขึ้นแบบไดนามิกในขณะรันไทม์

2. **การตั้งชื่อทรัพยากร**:

   - ทรัพยากรบางอย่างเท่านั้นที่ได้รับคำนำหน้าสภาพแวดล้อมในชื่อ (เช่น ตาราง `dev_ddb_export`, `dev-FrontendWebAcl`)
   - ทรัพยากรส่วนใหญ่คงชื่อเดิมไว้แต่ถูกแยกโดยอยู่ในสแต็กที่แตกต่างกัน

3. **การระบุสภาพแวดล้อม**:

   - ทรัพยากรทั้งหมดจะถูกแท็กด้วยแท็ก `CDKEnvironment` ที่มีชื่อสภาพแวดล้อม
   - คุณสามารถใช้แท็กนี้เพื่อระบุว่าทรัพยากรเป็นของสภาพแวดล้อมใด
   - ตัวอย่าง: `CDKEnvironment: dev` หรือ `CDKEnvironment: prod`

4. **การแทนที่สภาพแวดล้อมเริ่มต้น**: หากคุณกำหนดสภาพแวดล้อม "default" ใน `parameter.ts` มันจะแทนที่การตั้งค่าใน `cdk.json` หากต้องการใช้ `cdk.json` ต่อไป อย่ากำหนดสภาพแวดล้อม "default" ใน `parameter.ts`

5. **ข้อกำหนดสภาพแวดล้อม**: ในการสร้างสภาพแวดล้อมอื่นนอกเหนือจาก "default" คุณต้องใช้ `parameter.ts` ตัวเลือก `-c envName` เพียงอย่างเดียวไม่เพียงพอหากไม่มีการกำหนดสภาพแวดล้อมที่สอดคล้องกัน

6. **การแยกทรัพ

## อื่นๆ

คุณสามารถกำหนดพารามิเตอร์สำหรับการ deploy ได้สองวิธี: ใช้ `cdk.json` หรือใช้ไฟล์ `parameter.ts` ที่มีการตรวจสอบประเภทข้อมูล

#### การใช้ cdk.json (วิธีแบบดั้งเดิม)

วิธีดั้งเดิมในการกำหนดค่าพารามิเตอร์คือการแก้ไขไฟล์ `cdk.json` วิธีนี้ง่ายแต่ขาดการตรวจสอบประเภทข้อมูล:

```json
{
  "app": "npx ts-node --prefer-ts-exts bin/bedrock-chat.ts",
  "context": {
    "bedrockRegion": "us-east-1",
    "allowedIpV4AddressRanges": ["0.0.0.0/1", "128.0.0.0/1"],
    "selfSignUpEnabled": true
  }
}
```

#### การใช้ parameter.ts (วิธีที่แนะนำที่มีการตรวจสอบประเภทข้อมูล)

เพื่อการตรวจสอบประเภทข้อมูลที่ดีขึ้นและประสบการณ์การพัฒนาที่ดีกว่า คุณสามารถใช้ไฟล์ `parameter.ts` เพื่อกำหนดพารามิเตอร์ของคุณ:

```typescript
// กำหนดพารามิเตอร์สำหรับสภาพแวดล้อมเริ่มต้น
bedrockChatParams.set("default", {
  bedrockRegion: "us-east-1",
  allowedIpV4AddressRanges: ["192.168.0.0/16"],
  selfSignUpEnabled: true,
});

// กำหนดพารามิเตอร์สำหรับสภาพแวดล้อมเพิ่มเติม
bedrockChatParams.set("dev", {
  bedrockRegion: "us-west-2",
  allowedIpV4AddressRanges: ["10.0.0.0/8"],
  enableRagReplicas: false, // ประหยัดค่าใช้จ่ายสำหรับสภาพแวดล้อมการพัฒนา
});

bedrockChatParams.set("prod", {
  bedrockRegion: "us-east-1",
  allowedIpV4AddressRanges: ["172.16.0.0/12"],
  enableLambdaSnapStart: true,
  enableRagReplicas: true, // เพิ่มความพร้อมใช้งานสำหรับการผลิต
});
```

> [!Note]
> ผู้ใช้ที่มีอยู่สามารถใช้ `cdk.json` ต่อไปได้โดยไม่ต้องมีการเปลี่ยนแปลง วิธีการใช้ `parameter.ts` แนะนำสำหรับการ deploy ใหม่หรือเมื่อคุณต้องจัดการหลายสภาพแวดล้อม

### การ Deploy หลายสภาพแวดล้อม

คุณสามารถ deploy หลายสภาพแวดล้อมจากโค้ดเดียวกันโดยใช้ไฟล์ `parameter.ts` และตัวเลือก `-c envName`

#### ข้อกำหนดเบื้องต้น

1. กำหนดสภาพแวดล้อมของคุณใน `parameter.ts` ตามที่แสดงด้านบน
2. แต่ละสภาพแวดล้อมจะมีทรัพยากรของตัวเองพร้อมคำนำหน้าเฉพาะสภาพแวดล้อม

#### คำสั่งสำหรับ Deploy

เพื่อ deploy สภาพแวดล้อมเฉพาะ:

```bash
# Deploy สภาพแวดล้อมการพัฒนา
npx cdk deploy --all -c envName=dev

# Deploy สภาพแวดล้อมการผลิต
npx cdk deploy --all -c envName=prod
```

หากไม่ได้ระบุสภาพแวดล้อม จะใช้สภาพแวดล้อม "default":

```bash
# Deploy สภาพแวดล้อมเริ่มต้น
npx cdk deploy --all
```

#### หมายเหตุสำคัญ

1. **การตั้งชื่อ Stack**:

   - Stack หลักสำหรับแต่ละสภาพแวดล้อมจะมีคำนำหน้าด้วยชื่อสภาพแวดล้อม (เช่น `dev-BedrockChatStack`, `prod-BedrockChatStack`)
   - อย่างไรก็ตาม stack บอทที่กำหนดเอง (`BrChatKbStack*`) และ stack การเผยแพร่ API (`ApiPublishmentStack*`) จะไม่ได้รับคำนำหน้าสภาพแวดล้อมเนื่องจากถูกสร้างขึ้นแบบไดนามิกในขณะรันไทม์

2. **การตั้งชื่อทรัพยากร**:

   - ทรัพยากรบางอย่างเท่านั้นที่จะได้รับคำนำหน้าสภาพแวดล้อมในชื่อ (เช่น ตาราง `dev_ddb_export`, `dev-FrontendWebAcl`)
   - ทรัพยากรส่วนใหญ่ยังคงใช้ชื่อเดิมแต่ถูกแยกโดยอยู่ใน stack ที่แตกต่างกัน

3. **การระบุสภาพแวดล้อม**:

   - ทรัพยากรทั้งหมดจะถูกติดแท็กด้วยแท็ก `CDKEnvironment` ที่มีชื่อสภาพแวดล้อม
   - คุณสามารถใช้แท็กนี้เพื่อระบุว่าทรัพยากรนั้นเป็นของสภาพแวดล้อมใด
   - ตัวอย่าง: `CDKEnvironment: dev` หรือ `CDKEnvironment: prod`

4. **การแทนที่สภาพแวดล้อมเริ่มต้น**: หากคุณกำหนดสภาพแวดล้อม "default" ใน `parameter.ts` มันจะแทนที่การตั้งค่าใน `cdk.json` หากต้องการใช้ `cdk.json` ต่อไป อย่ากำหนดสภาพแวดล้อม "default" ใน `parameter.ts`

5. **ข้อกำหนดของสภาพแวดล้อม**: ในการสร้างสภาพแวดล้อมอื่นนอกเหนือจาก "default" คุณต้องใช้ `parameter.ts` การใช้ตัวเลือก `-c envName` เพียงอย่างเดียวไม่เพียงพอหากไม่มีการกำหนดสภาพแวดล้อมที่เกี่ยวข้อง

6. **การแยกทรัพยากร**: แต่ละสภาพแวดล้อมจะสร้างชุดทรัพยากรของตัวเอง ทำให้คุณสามารถมีสภาพแวดล้อมสำหรับการพัฒนา การทดสอบ และการผลิตในบัญชี AWS เดียวกันโดยไม่มีความขัดแย้ง

## อื่นๆ

### การลบทรัพยากร

หากใช้ cli และ CDK กรุณาใช้คำสั่ง `npx cdk destroy` หากไม่ได้ใช้ ให้เข้าไปที่ [CloudFormation](https://console.aws.amazon.com/cloudformation/home) จากนั้นลบ `BedrockChatStack` และ `FrontendWafStack` ด้วยตนเอง โปรดทราบว่า `FrontendWafStack` อยู่ในภูมิภาค `us-east-1`

### การตั้งค่าภาษา 

แอสเซทนี้ตรวจจับภาษาโดยอัตโนมัติโดยใช้ [i18next-browser-languageDetector](https://github.com/i18next/i18next-browser-languageDetector) คุณสามารถเปลี่ยนภาษาได้จากเมนูแอปพลิเคชัน หรือใช้ Query String เพื่อตั้งค่าภาษาดังตัวอย่างด้านล่าง

> `https://example.com?lng=ja`

### ปิดการลงทะเบียนด้วยตนเอง

ตัวอย่างนี้เปิดใช้งานการลงทะเบียนด้วยตนเองโดยค่าเริ่มต้น หากต้องการปิดการลงทะเบียนด้วยตนเอง ให้เปิดไฟล์ [cdk.json](./cdk/cdk.json) และเปลี่ยน `selfSignUpEnabled` เป็น `false` หากคุณกำหนดค่า [ผู้ให้บริการตัวตนภายนอก](#external-identity-provider) ค่านี้จะถูกละเว้นและปิดใช้งานโดยอัตโนมัติ

### จำกัดโดเมนสำหรับอีเมลที่ใช้ลงทะเบียน

โดยค่าเริ่มต้น ตัวอย่างนี้ไม่จำกัดโดเมนสำหรับอีเมลที่ใช้ลงทะเบียน หากต้องการอนุญาตการลงทะเบียนเฉพาะจากโดเมนที่กำหนด ให้เปิดไฟล์ `cdk.json` และระบุโดเมนเป็นรายการใน `allowedSignUpEmailDomains`

```ts
"allowedSignUpEmailDomains": ["example.com"],
```

### ผู้ให้บริการตัวตนภายนอก

ตัวอย่างนี้รองรับผู้ให้บริการตัวตนภายนอก ปัจจุบันเรารองรับ [Google](./idp/SET_UP_GOOGLE_th-TH.md) และ [ผู้ให้บริการ OIDC แบบกำหนดเอง](./idp/SET_UP_CUSTOM_OIDC_th-TH.md)

### WAF ส่วนหน้าแบบทางเลือก

สำหรับการกระจาย CloudFront WebACLs ของ AWS WAF ต้องถูกสร้างในภูมิภาค us-east-1 ในบางองค์กร การสร้างทรัพยากรนอกภูมิภาคหลักถูกจำกัดโดยนโยบาย ในสภาพแวดล้อมดังกล่าว การปรับใช้ CDK อาจล้มเหลวเมื่อพยายามจัดเตรียม Frontend WAF ใน us-east-1

เพื่อรองรับข้อจำกัดเหล่านี้ สแต็ก Frontend WAF จึงเป็นทางเลือก เมื่อปิดใช้งาน การกระจาย CloudFront จะถูกปรับใช้โดยไม่มี WebACL ซึ่งหมายความว่าคุณจะไม่มีการควบคุมการอนุญาต/ปฏิเสธ IP ที่ขอบส่วนหน้า การยืนยันตัวตนและการควบคุมแอปพลิเคชันอื่นๆ ทั้งหมดยังคงทำงานตามปกติ โปรดทราบว่าการตั้งค่านี้มีผลเฉพาะกับ Frontend WAF (ขอบเขต CloudFront) WAF ของ Published API (ระดับภูมิภาค) ยังคงไม่ได้รับผลกระทบ

หากต้องการปิดการใช้งาน Frontend WAF ให้ตั้งค่าต่อไปนี้ใน `parameter.ts` (วิธีที่แนะนำแบบ Type-Safe):

```ts
bedrockChatParams.set("default", {
  enableFrontendWaf: false
});
```

หรือหากใช้ `cdk/cdk.json` แบบเดิม ให้ตั้งค่าต่อไปนี้:

```json
"enableFrontendWaf": false
```

### เพิ่มผู้ใช้ใหม่เข้ากลุ่มโดยอัตโนมัติ

ตัวอย่างนี้มีกลุ่มต่อไปนี้เพื่อให้สิทธิ์แก่ผู้ใช้:

- [`Admin`](./ADMINISTRATOR_th-TH.md)
- [`CreatingBotAllowed`](#bot-personalization)
- [`PublishAllowed`](./PUBLISH_API_th-TH.md)

หากคุณต้องการให้ผู้ใช้ที่สร้างใหม่เข้าร่วมกลุ่มโดยอัตโนมัติ คุณสามารถระบุกลุ่มได้ใน [cdk.json](./cdk/cdk.json)

```json
"autoJoinUserGroups": ["CreatingBotAllowed"],
```

โดยค่าเริ่มต้น ผู้ใช้ที่สร้างใหม่จะถูกเพิ่มเข้ากลุ่ม `CreatingBotAllowed`

### กำหนดค่า RAG Replicas

`enableRagReplicas` เป็นตัวเลือกใน [cdk.json](./cdk/cdk.json) ที่ควบคุมการตั้งค่าเรพลิก้าสำหรับฐานข้อมูล RAG โดยเฉพาะ Knowledge Bases ที่ใช้ Amazon OpenSearch Serverless

- **ค่าเริ่มต้น**: true
- **true**: เพิ่มความพร้อมใช้งานโดยเปิดใช้งานเรพลิก้าเพิ่มเติม เหมาะสำหรับสภาพแวดล้อมการผลิตแต่เพิ่มค่าใช้จ่าย
- **false**: ลดค่าใช้จ่ายโดยใช้เรพลิก้าน้อยลง เหมาะสำหรับการพัฒนาและทดสอบ

นี่เป็นการตั้งค่าระดับบัญชี/ภูมิภาค ที่มีผลต่อแอปพลิเคชันทั้งหมดแทนที่จะเป็นบอทแต่ละตัว

> [!Note]
> ตั้งแต่มิถุนายน 2024 Amazon OpenSearch Serverless รองรับ 0.5 OCU ช่วยลดค่าใช้จ่ายเริ่มต้นสำหรับงานขนาดเล็ก การปรับใช้ในการผลิตสามารถเริ่มต้นด้วย 2 OCUs ในขณะที่งานพัฒนา/ทดสอบสามารถใช้ 1 OCU OpenSearch Serverless ปรับขนาดอัตโนมัติตามความต้องการของงาน สำหรับรายละเอียดเพิ่มเติม เยี่ยมชม [ประกาศ](https://aws.amazon.com/jp/about-aws/whats-new/2024/06/amazon-opensearch-serverless-entry-cost-half-collection-types/)

### กำหนดค่า Bot Store

คุณลักษณะ bot store ช่วยให้ผู้ใช้สามารถแชร์และค้นพบบอทที่กำหนดเอง คุณสามารถกำหนดค่า bot store ผ่านการตั้งค่าต่อไปนี้ใน [cdk.json](./cdk/cdk.json):

```json
{
  "context": {
    "enableBotStore": true,
    "enableBotStoreReplicas": false,
    "botStoreLanguage": "en"
  }
}
```

- **enableBotStore**: ควบคุมว่าจะเปิดใช้งานคุณลักษณะ bot store หรือไม่ (ค่าเริ่มต้น: `true`)
- **botStoreLanguage**: กำหนดภาษาหลักสำหรับการค้นหาและค้นพบบอท (ค่าเริ่มต้น: `"en"`) ส่งผลต่อวิธีการทำดัชนีและค้นหาบอทใน bot store โดยปรับการวิเคราะห์ข้อความให้เหมาะสมกับภาษาที่ระบุ
- **enableBotStoreReplicas**: ควบคุมว่าจะเปิดใช้งานเรพลิก้าสแตนด์บายสำหรับคอลเลกชัน OpenSearch Serverless ที่ใช้โดย bot store หรือไม่ (ค่าเริ่มต้น: `false`) การตั้งค่าเป็น `true` จะช่วยเพิ่มความพร้อมใช้งานแต่เพิ่มค่าใช้จ่าย ในขณะที่ `false` จะลดค่าใช้จ่ายแต่อาจส่งผลต่อความพร้อมใช้งาน
  > **สำคัญ**: คุณไม่สามารถอัปเดตคุณสมบัตินี้หลังจากที่สร้างคอลเลกชันแล้ว หากคุณพยายามแก้ไขคุณสมบัตินี้ คอลเลกชันจะยังคงใช้ค่าเดิม

### การอนุมานข้ามภูมิภาค

[การอนุมานข้ามภูมิภาค](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html) ช่วยให้ Amazon Bedrock สามารถกำหนดเส้นทางคำขออนุมานโมเดลข้ามภูมิภาค AWS หลายภูมิภาคแบบไดนามิก เพื่อเพิ่มประสิทธิภาพและความยืดหยุ่นในช่วงที่มีความต้องการสูง หากต้องการกำหนดค่า ให้แก้ไข `cdk.json`

```json
"enableBedrockCrossRegionInference": true
```

### Lambda SnapStart

[Lambda SnapStart](https://docs.aws.amazon.com/lambda/latest/dg/snapstart.html) ช่วยปรับปรุงเวลาเริ่มต้นเย็นสำหรับฟังก์ชัน Lambda ให้ตอบสนองได้เร็วขึ้นเพื่อประสบการณ์ผู้ใช้ที่ดีขึ้น ในทางกลับกัน สำหรับฟังก์ชัน Python จะมี[ค่าใช้จ่ายขึ้นอยู่กับขนาดแคช](https://aws.amazon.com/lambda/pricing/#SnapStart_Pricing) และ[ไม่พร้อมใช้งานในบางภูมิภาค](https://docs.aws.amazon.com/lambda/latest/dg/snapstart.html#snapstart-supported-regions) ในปัจจุบัน หากต้องการปิดการใช้งาน SnapStart ให้แก้ไข `cdk.json`

```json
"enableLambdaSnapStart": false
```

### กำหนดค่าโดเมนแบบกำหนดเอง

คุณสามารถกำหนดค่าโดเมนแบบกำหนดเองสำหรับการกระจาย CloudFront โดยตั้งค่าพารามิเตอร์ต่อไปนี้ใน [cdk.json](./cdk/cdk.json):

```json
{
  "alternateDomainName": "chat.example.com",
  "hostedZoneId": "Z0123456789ABCDEF"
}
```

- `alternateDomainName`: ชื่อโดเมนแบบกำหนดเองสำหรับแอปพลิเคชันแชทของคุณ (เช่น chat.example.com)
- `hostedZoneId`: ID ของโซนโฮสต์ Route 53 ที่จะสร้างเรคอร์ดโดเมน

เม

## ติดต่อ

- [Takehiro Suzuki](https://github.com/statefb)
- [Yusuke Wada](https://github.com/wadabee)
- [Yukinobu Mine](https://github.com/Yukinobu-Mine)

## 🏆 ผู้มีส่วนร่วมที่สำคัญ

- [fsatsuki](https://github.com/fsatsuki)
- [k70suK3-k06a7ash1](https://github.com/k70suK3-k06a7ash1)

## ผู้มีส่วนร่วม

[![bedrock chat contributors](https://contrib.rocks/image?repo=aws-samples/bedrock-chat&max=1000)](https://github.com/aws-samples/bedrock-chat/graphs/contributors)

## การอนุญาตใช้งาน

ไลบรารีนี้ได้รับอนุญาตภายใต้สัญญาอนุญาต MIT-0 โปรดดู[ไฟล์การอนุญาตใช้งาน](./LICENSE)