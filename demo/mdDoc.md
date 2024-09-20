<a name="Ef6XA"></a>
## 解析结论
Langchain-chatchat处理文本后的原始分段语义比较完整，但缺少图片的提取和表格提取<br />UnstructuredWordDocumentLoader抽取表格效果不错，支持跨页的提取,不支持图片提取<br />Rag-flow:DeepDoc 在提取元素时，按标题进行了树形结构的格式化处理，每个文本前缀都包含了标题信息，但是缺少分段的metaInfo信息

可以以Rag-flow:DeepDoc为起点，增强图片的提取和标题的梳理，参考另外两个项目，补充meta的信息，最后输出树状结构的文本分段,要求用户提供的docx文档包含目录结构，且不要是其他格式转换，不要使用老的doc格式
<a name="y30TT"></a>
### 元素提取对比
这是docx文档内部的xml格式，提取文本/表格/图片也是基于此进行<br />![](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722758244308-cd0d8315-47fb-4066-b773-a03f4fb0a261.png#averageHue=%237f807a&clientId=ub420aeee-35df-4&from=paste&id=f5IV5&originHeight=585&originWidth=864&originalType=url&ratio=1&rotation=0&showTitle=false&status=done&style=none&taskId=u4f827e43-aceb-4d13-be9c-1b698b96f91&title=)
<a name="vqk3h"></a>
### 文档场景对比
<a name="dgQ41"></a>
#### 场景对比
总的来说，只要是来源于pdf转换的，xml信息都会有缺失，导致识别处理问题很大，实际使用应该避免这样的转换，直接采用pdf识别即可

| 解析方案 | 简历(复杂格式) | 政府前瞻规划(文本) | 问界功能手册(图+文本+表格+pdf转换) | 行业规划(大量图表+pdf转换+无目录) |
| --- | --- | --- | --- | --- |
| UnstructuredWordDocumentLoader | 无法解析 | 好 | 一般 | 差 |
| Langchain-chatchat | 无法解析 | 好 | 差 | 差 |
| Rag-flow:DeepDoc | 无法解析 | 好 | 好 | 无法解析 |

<a name="gJxYT"></a>
#### 场景截图
<a name="nW2Kx"></a>
##### 简历：
![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722741852437-d366a734-ffec-43ca-9fe4-61f0d9099c91.png#averageHue=%23848874&clientId=u00e935eb-204d-4&from=paste&height=690&id=u90b4ebc2&originHeight=690&originWidth=806&originalType=binary&ratio=1.5&rotation=0&showTitle=false&size=189246&status=done&style=none&taskId=u1cd98096-11b7-4816-aace-286d91a8e72&title=&width=806)
<a name="kLNt5"></a>
##### 政府前瞻规划
![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722741881696-bfe053f4-7df2-4b12-a590-3c3941b22554.png#averageHue=%23f7f7f7&clientId=u00e935eb-204d-4&from=paste&height=550&id=uabf26755&originHeight=550&originWidth=1310&originalType=binary&ratio=1.5&rotation=0&showTitle=false&size=46719&status=done&style=none&taskId=u1496649b-66f9-4f02-b4d8-838ecbb0c9b&title=&width=1310)<br />![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722741901630-eec401d3-cd04-4b36-a597-f60ddd6931b1.png#averageHue=%23e8e8e8&clientId=u00e935eb-204d-4&from=paste&height=880&id=u7a35632b&originHeight=880&originWidth=1381&originalType=binary&ratio=1.5&rotation=0&showTitle=false&size=183918&status=done&style=none&taskId=u40bdd37f-f93f-4889-96c6-163580f2349&title=&width=1381)
<a name="qf679"></a>
##### 问界使用手册

<a name="QEaRl"></a>
##### 行业调研报告
![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722742010896-d140d4f4-7680-41e7-ac55-95b7de32d8de.png#averageHue=%23b0bfb3&clientId=u00e935eb-204d-4&from=paste&height=832&id=u246a4e0e&originHeight=832&originWidth=1275&originalType=binary&ratio=1.5&rotation=0&showTitle=false&size=1443029&status=done&style=none&taskId=u41a8ff03-7f47-4a64-91ba-9d747353cfc&title=&width=1275)<br />![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722742025221-fcdfef9a-aee2-475c-a4c3-9c98694d049e.png#averageHue=%23f8f9f8&clientId=u00e935eb-204d-4&from=paste&height=740&id=u1201ad71&originHeight=740&originWidth=1246&originalType=binary&ratio=1.5&rotation=0&showTitle=false&size=158025&status=done&style=none&taskId=ua723b78f-1963-4eb9-9344-900ddea8639&title=&width=1246)
<a name="ex9cZ"></a>
## UnstructuredWordDocumentLoader
开源项目中Qanything和Langchain-chatchat都使用了这个Loader来解析doc文档，只是额外补充了信息<br />**优势**：基于规则，速度快，同时因为提取的是所有文本，不存在跨页的问题，本身就有不错的分段效果<br />**劣势**:   本身不支持图片的提取，对于其他格式比如pdf/doc转换得到的docx解析效果不好，因为xml信息不够

每个解析出来的元素由metadata和page_content构成<br />page_content就是纯文本<br />meta_data则是标识列该元素块的一些属性，比如emphasized_text_contents，对应emphasized_text_tags能知道强调的内容，一般可以作为关键词使用<br />category标识了元素的类型
```json
{'source': 'docs/新能源汽车发展政府规划.docx', 
  'category_depth': 0, 
  'emphasized_text_contents': ['3', '.', '创新能力显著提升', '，智能化', '水平进一步提高', '。'], 
  'emphasized_text_tags': ['b', 'b', 'b', 'b', 'b', 'b'], 
  'last_modified': '2024-08-03T19:05:25', 
  'page_number': 5, 'languages': ['zho', 'kor'], 
  'file_directory': 'docs', 
  'filename': '新能源汽车发展政府规划.docx', 
  'filetype': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 
  'category': 'Title',
  'element_id': '36249e96685cc45214f87a04140679df'}
```
<a name="p1wYY"></a>
### 场景实践
<a name="Vn4OI"></a>
#### 简历抽取-复杂格式(❌)
完全提取不出任何文本信息，因为简历格式太复杂了，unstructure无法处理
<a name="Vtpel"></a>
#### 政府前瞻规划(目录/文本/图片/表格)
<a name="dl4jy"></a>
##### 文本抽取(✅)
因为本身由docx写的，xml信息足够丰富，文本的提取比较好，且分块比较合理，表格抽取也能解决跨页的问题<br />![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722685211498-5e891289-feb3-4b63-bf31-b7f5b18b28b6.png#averageHue=%23eaeaea&clientId=ue4110d4f-3708-4&from=paste&height=548&id=xfy6k&originHeight=1008&originWidth=826&originalType=binary&ratio=1.125&rotation=0&showTitle=false&size=113031&status=done&style=none&taskId=ubd220b12-d991-40d3-8b17-12d7171e756&title=&width=449.22222900390625)
```python
page_content= """3.创新能力显著提升，智能化水平进一步提高。
“十三五”期间，杭州市以汽车生产制造企业、核心零部件龙头企业为主体，通过联合国内外高等院校、科研机构成立企业技术中心，通过国际合作等方式，
突破核心零部件关键技术。同时，积极引导汽车企业开展智能化升级改造，推动传统制造业数智化转型。
截至2020年，全市汽车产业拥有国家级企业技术中心6个、省级企业技术中心15个、市级企业技术中心23个，实施数字化改造项目44个，成功创建4家智能工厂和10余个数字化车间。
春风动力入选浙江省首批"""
metadata = {'source': 'docs/新能源汽车发展政府规划.docx', 
     'emphasized_text_contents': ['3', '.', '创新能力显著提升', '，智能化', '水平进一步提高', '。'], 
     'emphasized_text_tags': ['b', 'b', 'b', 'b', 'b', 'b'], 
     'page_number': 5,
     'filename': '新能源汽车发展政府规划.docx', 
     'category': 'Title',
    }
```
跨页标识
```python
page_content=''
metadata={'source': 'docs/新能源汽车发展政府规划.docx', 
          'filename': '新能源汽车发展政府规划.docx', 'category': 'PageBreak', 
          'emphasized_text_contents': None, 
          'emphasized_text_tags': None, 
          'page_number': None}, 
        
```
续接上一页
```python
page_content='“未来工厂”，亚太机电“智能汽车+车联网+新能源汽车轮毂电机”发展模式全国首创，首批产品已于2018年1月正式下线，初步实现产业化。万向集团通过国际化并购，整合全球电池研发资源，成立了万向集团电池国际创新中心。'
metadata={'source': 'docs/新能源汽车发展政府规划.docx', 
          'filename': '新能源汽车发展政府规划.docx', 
          'category': 'Title', 
          'emphasized_text_contents': None, 
          'emphasized_text_tags': None, 
          'page_number': 7}
```
<a name="PinXm"></a>
##### 表格抽取(✅)
![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722683188399-ba9f1ad8-2c93-4f54-87ec-0ee8b9f0a31c.png#averageHue=%23ececec&clientId=ue4110d4f-3708-4&from=paste&height=568&id=t0YcA&originHeight=1017&originWidth=759&originalType=binary&ratio=1.125&rotation=0&showTitle=false&size=90232&status=done&style=none&taskId=u2b1b12d1-fdef-403e-9cbf-880faaac049&title=&width=423.66668701171875)<br />表格直接被处理了多段文本，category识别也有问题
```html
page_content="专栏5：智能网联汽车测试示范区建设 1.封闭测试：升级改造传统汽车试验场，或充分利用半开放的园区、景区、校园、机场、港口等建设一体化测试场，拓展封闭测试场的承载空间，满足T1至T5 的测试需求。 2.半开放道路测试：支持在港口、矿区、物流园区等封闭场所开展无人物流服务，逐步开展多场景无人物流示范。以万向创新聚能城、信息港小镇、未来交通小镇等重点园区为载体，推动智慧公交及智慧高速应用场景建设。依托湘湖旅游度假景区、杭州萧山国际机场等特定区域，围绕自动驾驶巡逻、无人清扫、短程接驳及自主泊车等场景，开展智能网联汽车示范应用。 3.开放道路测试：在萧山、余杭、钱塘区等区域开放杭州市第二批智能网联汽车开放测试道路，并逐步扩大至杭州市全域的道路开放。重点在“亚运三村四区块”以及主体育馆、游泳馆、综合训练馆、党湾未来交通小镇及湘湖旅游度假区等区域开放道路测试。 4.无人驾驶应用：推动亚运会场馆周边区域道路智能化改造，鼓励并支持相关企业积极参与亚运区域自动驾驶示范应用项目，开展自动驾驶网约车服务、自动驾驶短程接驳、无人物流、无人环卫等应用。"
metadata={'source': 'docs/新能源汽车发展政府规划.docx', 
 'emphasized_text_contents': ['1.', '封闭测试：', '2.', '半开放道路测试：', '3.', '开放道路测试：'], 'emphasized_text_tags': ['b', 'b', 'b', 'b', 'b', 'b'], 
 'last_modified': '2024-08-03T19:05:25', 'page_number': 25, 
 'text_as_html': '<table>\n
   <thead>\n
     <tr><th>专栏5：智能网联汽车测试示范区建设</th></tr>\n
   </thead>\n
   <tbody>\n
     <tr>
       <td>1.封闭测试：升级改造传统汽车试验场，或充分利用半开放的园区、景区、校园、机场、港口等建设一体化测试场，拓展封闭测试场的承载空间，满足T1至T5 的测试需求。
         \n2.半开放道路测试：支持在港口、矿区、物流园区等封闭场所开展无人物流服务，逐步开展多场景无人物流示范。以万向创新聚能城、信息港小镇、未来交通小镇等重点园区为载体，
         推动智慧公交及智慧高速应用场景建设。依托湘湖旅游度假景区、杭州萧山国际机场等特定区域，围绕自动驾驶巡逻、无人清扫、短程接驳及自主泊车等场景，开展智能网联汽车示范应用。
         \n3.开放道路测试：在萧山、余杭、钱塘区等区域开放杭州市第二批智能网联汽车开放测试道路，并逐步扩大至杭州市全域的道路开放。重点在“亚运三村四区块”以及主体育馆、游泳馆、综合训练馆、党湾未来交通小镇及湘湖旅游度假区等区域开放道路测试。
         \n4.无人驾驶应用：推动亚运会场馆周边区域道路智能化改造，鼓励并支持相关企业积极参与亚运区域自动驾驶示范应用项目，开展自动驾驶网约车服务、自动驾驶短程接驳、无人物流、无人环卫等应用。
       </td>
     </tr>\n
   </tbody>\n
 </table>', 
'filename': '新能源汽车发展政府规划.docx', 
'category': 'Table'}
```
| 专栏2：构建智能网联汽车产业生态 |
| --- |
| 1. 推动智能汽车测试服务。支持市内企业和科研机构建设智能汽车仿真测试与研发平台，提供各类增值及管理服务，实现多主体互利共赢。 |
| 2. 探索车载综合信息服务。利用车载互联网平台，导入地图、商业、旅行、交通等信息服务业务，引导智能汽车企业积极协同阿里巴巴等互联网企业，充分利用云计算、大数据等先进技术，挖掘工作、生活和娱乐等多元化的需求，创新车载信息服务模式，促进智能汽车产业链向后端延伸。 |
| 3. 推进大数据服务。向企业和科研机构开放交通大数据，建设城市数据平台。围绕跨领域大数据的应用，实现智能汽车的商业模式创新、全生命周期的安全管理。 |
| 4. 促进定位服务与高精度地图商业应用。依托高德地图等企业，重点突破高精度定位技术，实现地图数据自动化处理、地图数据质量检查、海量高精度地图数据存储管理等规模化、自动化的服务。 |
| 5. 培育自动驾驶出行服务。鼓励车企与运营服务商合作，开展无人驾驶+共享出行服务。在萧山、滨江、余杭等地率先开展基于无人驾驶汽车的无人公交、无人物流、移动零售、移动办公等新型服务业。拓展车联网商业化空间，挖掘特定场景应用价值。 |
| 6. 发展智能汽车金融保险服务。鼓励保险企业积极探索自动驾驶在路测、试运营以及商业化阶段保险机制，调整保险范围、赔偿机制，创新保险产品。鼓励发展二手车、汽车租赁等金融服务，加快建立智能汽车产业金融支持体系。 |

<a name="POACr"></a>
##### 图片抽取(❌)
<a name="avJYW"></a>
#### 问界功能手册(目录/文本/表格 / 图片)
<a name="CMVzK"></a>
##### 文本抽取(✅)
![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722743989467-e22897f7-329f-4571-9be5-c89b0f08f63b.png#averageHue=%23f8f8f6&clientId=u00e935eb-204d-4&from=paste&height=201&id=u78ce37ad&originHeight=201&originWidth=624&originalType=binary&ratio=1.5&rotation=0&showTitle=false&size=13970&status=done&style=none&taskId=u0b1aa38c-3d71-47a5-af51-70cd6005367&title=&width=624)
```python
page_content='用车建议' 
metadata={'source': 'docs/问界使用说明书_部分.docx', 
          'page_number': 1, 'filename': '问界使用说明书_部分.docx',  'category': 'Title'}
```
```python
page_content='在本章中，您可了解驾驶车辆时的注意事项及车辆日常养护，请仔细阅读本部分。' 
metadata={'source': 'docs/问界使用说明书_部分.docx', 
          'filename': '问界使用说明书_部分.docx', 
          'category': 'Title'}
```
<a name="bu9Jd"></a>
##### 表格提取(✅)
![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722743770910-542856e5-2870-483a-b723-d0655b853a24.png#averageHue=%23fafafa&clientId=u00e935eb-204d-4&from=paste&height=301&id=u49fbd739&originHeight=301&originWidth=690&originalType=binary&ratio=1.5&rotation=0&showTitle=false&size=19250&status=done&style=none&taskId=ub7e52686-9d3b-49bd-9116-687ae20c3aa&title=&width=690)
```python
page_content='加油口盖 ( 282 页) 全景环视摄像头 ( 172 页) 行李支撑架 ( 111 页) 车辆牌照位置 激光雷达 超声波雷达 侧视摄像头 轮胎 ( 299 页) 前风挡雨刮 ( 102 页) 全景环视摄像头 ( 172 页) 前照灯 ( 93 页) 车门外把手 ( 63 页) 车标 —'
metadata={'source': 'docs/问界使用说明书_部分.docx', 'last_modified': '2024-08-04T11:47:39', 'page_number': 6, 
           'filename': '问界使用说明书_部分.docx',  'category': 'Table'
         'text_as_html':
          """   
<table>
<thead>
<tr><th> 加油口盖 ( 282 页)  </th><th> 全景环视摄像头 ( 172 页)  </th></tr>
</thead>
<tbody>
<tr><td>行李支撑架 ( 111 页)  </td><td>车辆牌照位置             </td></tr>
<tr><td>激光雷达            </td><td>超声波雷达              </td></tr>
<tr><td>侧视摄像头           </td><td>轮胎 ( 299 页)        </td></tr>
<tr><td>前风挡雨刮 ( 102 页)  </td><td>全景环视摄像头 ( 172 页)   </td></tr>
<tr><td>前照灯 ( 93 页)     </td><td>车门外把手 ( 63 页)      </td></tr>
<tr><td>车标              </td><td>—                  </td></tr>
</tbody>
</table>
"""}
```
| 加油口盖 ( 282 页) | 全景环视摄像头 ( 172 页) |
| --- | --- |
| 行李支撑架 ( 111 页) | 车辆牌照位置 |
| 激光雷达 | 超声波雷达 |
| 侧视摄像头 | 轮胎 ( 299 页) |
| 前风挡雨刮 ( 102 页) | 全景环视摄像头 ( 172 页) |
| 前照灯 ( 93 页) | 车门外把手 ( 63 页) |
| 车标 | - |

<a name="pUNbr"></a>
##### 图片抽取(❌)
<a name="A9FiM"></a>
#### 行业调研报告(文本/表格/图片)
<a name="rSzyc"></a>
##### 文本抽取(✅)
对于其他格式转换得到的docx解析很差，因为xml中缺少元素信息，造成原始的分段和类型的识别都出现问题<br />![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722690671825-7d10f814-051b-4962-9dfb-ee83a0a37329.png#averageHue=%23e6e7e9&clientId=ue4110d4f-3708-4&from=paste&height=311&id=CqZSH&originHeight=389&originWidth=705&originalType=binary&ratio=1.125&rotation=0&showTitle=false&size=37997&status=done&style=none&taskId=u95c6a415-e78b-4e47-a1bd-dfe445d5b15&title=&width=564)
```python
page_content='一、驶向2030—汽车行业竞速赛' 
metadata={'source': 'docs/行业研究.docx', 'filename': '行业研究.docx', 'category': 'Title'}

page_content='我们正在经历的，是汽车行业的又   — 核心胜负手变革：“爆款”车辆的'
metadata={'source': 'docs/行业研究.docx',  'filename': '行业研究.docx', 'category': 'Title'}

page_content='一次伟大变革。自19世纪80年代'
metadata={'source': 'docs/行业研究.docx',  'filename': '行业研究.docx', 'category': 'Title'}

```
<a name="LWGgA"></a>
##### 表格提取(❌)
非docx标准表格，由图片+无线表格组成提取不了,会直接分段为普通文字<br />![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722749230562-abcdb005-2187-4ae5-b82c-6cf55480f252.png#averageHue=%23fdfdfd&clientId=u00e935eb-204d-4&from=paste&height=585&id=ufc59abd6&originHeight=585&originWidth=661&originalType=binary&ratio=1.5&rotation=0&showTitle=false&size=114757&status=done&style=none&taskId=u59ca8a16-7ee1-4298-ac5f-3f148f31294&title=&width=661)<br />![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722749846045-4c7221b3-16cc-468e-a291-e71f9c36e381.png#averageHue=%23fdfdfd&clientId=u00e935eb-204d-4&from=paste&height=864&id=u5ef3ca68&originHeight=864&originWidth=674&originalType=binary&ratio=1.5&rotation=0&showTitle=false&size=100260&status=done&style=none&taskId=u296f4fd9-7011-4bc8-9984-310df892fcc&title=&width=674)
```python
page_content='图5即便在中低线城市的中型以上细分市场，电动汽车'
metadata={'source': 'docs/行业研究.docx', 
                   'filename': '行业研究.docx', 'category': 'Title', 
                   'emphasized_text_contents': None, 
                   'emphasized_text_tags': None,
                   'page_number': None}

page_content='渗透率也同样实现了巨大提升'
metadata={'source': 'docs/行业研究.docx', 
                   'filename': '行业研究.docx', 'category': 'Title', 
                   'emphasized_text_contents': None, 
                   'emphasized_text_tags': None,
                   'page_number': None}
page_content='电动汽车渗透率 2022年 (1~9月份)'
metadata={'source': 'docs/行业研究.docx', 
                   'filename': '行业研究.docx', 'category': 'Title', 
                   'emphasized_text_contents': None, 
                   'emphasized_text_tags': None,
                   'page_number': None}
page_content='2020年'
metadata={'source': 'docs/行业研究.docx', 
                   'filename': '行业研究.docx', 'category': 'Title', 
                   'emphasized_text_contents': None, 
                   'emphasized_text_tags': None,
                   'page_number': None}
page_content='百分比'
metadata={'source': 'docs/行业研究.docx', 
                   'filename': '行业研究.docx', 'category': 'Title', 
                   'emphasized_text_contents': None, 
                   'emphasized_text_tags': None,
                   'page_number': None}
```
<a name="P03nV"></a>
##### 图片提取(❌)
<a name="BkEpi"></a>
## Langchain-chatchat内置实现
该项目整体为一个rag项目，关于docloader的部分，基于UnstructuredWordDocumentLoader结合了rapidOCR进行了图片的识别和提取，但是完全是只处理文本信息，会读取表格中的每个cell文本，再结合ocr识别的每张图片的文本

**优势**：结合了UnstructuredWordDocumentLoader，同时也支持了图片的提取和ocr识别，解析速度够快<br />**劣势**:   对于非标准格式产生的docx解析效果同样很差，且完全是提取文本的逻辑，不会提取表格和图片

每个解析出来的元素由metadata和page_content构成<br />page_content就是纯文本<br />meta_data则是标识列该元素块的一些属性，比如emphasized_text_contents，对应emphasized_text_tags能知道强调的内容，一般可以作为关键词使用<br />category标识了元素的类型
```json
{'source': 'docs/新能源汽车发展政府规划.docx', 
  'category_depth': 0, 
  'emphasized_text_contents': ['3', '.', '创新能力显著提升', '，智能化', '水平进一步提高', '。'], 
  'emphasized_text_tags': ['b', 'b', 'b', 'b', 'b', 'b'], 
  'last_modified': '2024-08-03T19:05:25', 
  'page_number': 5, 'languages': ['zho', 'kor'], 
  'file_directory': 'docs', 
  'filename': '新能源汽车发展政府规划.docx', 
  'filetype': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 
  'category': 'Title',
  'element_id': '36249e96685cc45214f87a04140679df'}
```
<a name="CQkvX"></a>
### 场景实践
<a name="lzMch"></a>
#### 简历抽取(复杂格式)(❌)
完全提取不出任何文本信息，因为简历格式太复杂了，unstructure无法处理
<a name="ua5gt"></a>
#### 政府前瞻规划(目录/文本/图片/表格)
<a name="iZtsT"></a>
##### 文本抽取(✅)
因为传入的是所有文本信息，这里不再保留break块，整个是一个完整的语段<br />![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722685211498-5e891289-feb3-4b63-bf31-b7f5b18b28b6.png#averageHue=%23eaeaea&clientId=ue4110d4f-3708-4&from=paste&height=548&id=tGDpq&originHeight=1008&originWidth=826&originalType=binary&ratio=1.125&rotation=0&showTitle=false&size=113031&status=done&style=none&taskId=ubd220b12-d991-40d3-8b17-12d7171e756&title=&width=449.22222900390625)
```python
page_content="""3.创新能力显著提升，智能化水平进一步提高。
“十三五”期间，杭州市以汽车生产制造企业、核心零部件龙头企业为主体，通过联合国内外高等院校、科研机构成立企业技术中心，通过国际合作等方式，突破核心零部件关键技术。
同时，积极引导汽车企业开展智能化升级改造，推动传统制造业数智化转型。截至2020年，全市汽车产业拥有国家级企业技术中心6个、省级企业技术中心15个、市级企业技术中心23个，实施数字化改造项目44个，成功创建4家智能工厂和10余个数字化车间。
春风动力入选浙江省首批“未来工厂”，亚太机电“智能汽车+车联网+新能源汽车轮毂电机”发展模式全国首创，
首批产品已于2018年1月正式下线，初步实现产业化。
万向集团通过国际化并购，整合全球电池研发资源，成立了万向集团电池国际创新中心。"""
metadata={'source': 'docs/新能源汽车发展政府规划.docx', 
           'category': 'Title'}
```
<a name="l9GzF"></a>
##### 表格抽取(❌)
![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722683188399-ba9f1ad8-2c93-4f54-87ec-0ee8b9f0a31c.png#averageHue=%23ececec&clientId=ue4110d4f-3708-4&from=paste&height=568&id=pl2l4&originHeight=1017&originWidth=759&originalType=binary&ratio=1.125&rotation=0&showTitle=false&size=90232&status=done&style=none&taskId=u2b1b12d1-fdef-403e-9cbf-880faaac049&title=&width=423.66668701171875)
```python
page_content='专栏4：突破智能网联汽车关键技术和平台'
metadata={'source': 'docs/新能源汽车发展政府规划.docx', 
          'filename': None, 'category': 'Title', 
          'emphasized_text_contents': None, 
          'emphasized_text_tags': None, 
          'page_number': None},
   

page_content='1.环境感知技术：重点突破雷达探测、机器视觉、车辆姿态感知、乘员状态感知和协同感知技术，支持杰华特、大立微电子、兰特普等企业在车规级毫米波雷达、红外夜视、激光雷达等专业特定领域实现技术突破。'
metadata={'source': 'docs/新能源汽车发展政府规划.docx', 
          'filename': None, 'category': 'Title', 
          'emphasized_text_contents': None,
          'emphasized_text_tags': None, 
          'page_number': None}


page_content='2.规划决策技术：加强在边缘计算、大数据、人工智能、多源异构计算、云计算模型库建设、云端数据分级共享技术等方面进行技术和产业布局，强化云端汽车大脑运算和决策能力，突破多车协同规划和智能决策技术。' 
metadata={'source': 'docs/新能源汽车发展政府规划.docx', 
          'filename': None, 'category': 'Title', 
          'emphasized_text_contents': None, 
          'emphasized_text_tags': None, 
          'page_number': None}

page_content='3.控制执行技术：重点突破下一代智能汽车的单车智能控制和多车协同控制技术，搭建适用于不同级别智能汽车控制策略开发的测试仿真平台，探索深度学习与增强学习在智能汽车决策控制技术开发中的应用。'
metadata={'source': 'docs/新能源汽车发展政府规划.docx', 
          'filename': None, 'category': 'Title', 
          'emphasized_text_contents': None, 
          'emphasized_text_tags': None, 
          'page_number': None}

page_content='4.智能汽车软件平台：针对智能汽车应用的高安全、高可靠、强实时等需求，攻克面向异构多处理硬件平台的智能汽车操作系统关键技术，满足实时控制、高性能计算和安全防护的要求。' 
metadata={'source': 'docs/新能源汽车发展政府规划.docx', 
          'filename': None, 'category': 'Title', 
          'emphasized_text_contents': None, 
          'emphasized_text_tags': None, 
          'page_number': None}

page_content='5.车联网云控平台：建立车联网系统架构，打通车端、路端数据，开发数据应用，支撑多级别的智能驾驶与新一代智能交通发展，服务政府管理、企业研发和用户出行需要。' 
metadata={'source': 'docs/新能源汽车发展政府规划.docx', 
          'filename': None, 'category': 'Title', 
          'emphasized_text_contents': None, 
          'emphasized_text_tags': None, 
          'page_number': None}
```
<a name="zS6Nh"></a>
##### 图片抽取(❌)

<a name="rf00U"></a>
#### 问界功能手册(目录/文本/表格/图片)
<a name="CkeUS"></a>
##### 文本抽取(✅)
![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722743989467-e22897f7-329f-4571-9be5-c89b0f08f63b.png#averageHue=%23f8f8f6&clientId=u00e935eb-204d-4&from=paste&height=201&id=g9Fk5&originHeight=201&originWidth=624&originalType=binary&ratio=1.5&rotation=0&showTitle=false&size=13970&status=done&style=none&taskId=u0b1aa38c-3d71-47a5-af51-70cd6005367&title=&width=624)
```python
page_content='用车建议' 
metadata={'source': 'docs/问界使用说明书_部分.docx', 
          'page_number': 1, 'filename': '问界使用说明书_部分.docx',  'category': 'Title'}
```
```python
page_content='在本章中，您可了解驾驶车辆时的注意事项及车辆日常养护，请仔细阅读本部分。' 
metadata={'source': 'docs/问界使用说明书_部分.docx', 
          'filename': '问界使用说明书_部分.docx', 
          'category': 'Title'}
```
<a name="fXq5d"></a>
##### 表格提取(✅)
![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722743770910-542856e5-2870-483a-b723-d0655b853a24.png#averageHue=%23fafafa&clientId=u00e935eb-204d-4&from=paste&height=301&id=vnPdV&originHeight=301&originWidth=690&originalType=binary&ratio=1.5&rotation=0&showTitle=false&size=19250&status=done&style=none&taskId=ub7e52686-9d3b-49bd-9116-687ae20c3aa&title=&width=690)
```python
page_content='加油口盖 ( 282 页) 全景环视摄像头 ( 172 页) 行李支撑架 ( 111 页) 车辆牌照位置 激光雷达 超声波雷达 侧视摄像头 轮胎 ( 299 页) 前风挡雨刮 ( 102 页) 全景环视摄像头 ( 172 页) 前照灯 ( 93 页) 车门外把手 ( 63 页) 车标 —'
metadata={'source': 'docs/问界使用说明书_部分.docx', 'last_modified': '2024-08-04T11:47:39', 'page_number': 6, 
           'filename': '问界使用说明书_部分.docx',  'category': 'Table'
         'text_as_html':
          """   
<table>
<thead>
<tr><th> 加油口盖 ( 282 页)  </th><th> 全景环视摄像头 ( 172 页)  </th></tr>
</thead>
<tbody>
<tr><td>行李支撑架 ( 111 页)  </td><td>车辆牌照位置             </td></tr>
<tr><td>激光雷达            </td><td>超声波雷达              </td></tr>
<tr><td>侧视摄像头           </td><td>轮胎 ( 299 页)        </td></tr>
<tr><td>前风挡雨刮 ( 102 页)  </td><td>全景环视摄像头 ( 172 页)   </td></tr>
<tr><td>前照灯 ( 93 页)     </td><td>车门外把手 ( 63 页)      </td></tr>
<tr><td>车标              </td><td>—                  </td></tr>
</tbody>
</table>
"""}
```
| 加油口盖 ( 282 页) | 全景环视摄像头 ( 172 页) |
| --- | --- |
| 行李支撑架 ( 111 页) | 车辆牌照位置 |
| 激光雷达 | 超声波雷达 |
| 侧视摄像头 | 轮胎 ( 299 页) |
| 前风挡雨刮 ( 102 页) | 全景环视摄像头 ( 172 页) |
| 前照灯 ( 93 页) | 车门外把手 ( 63 页) |
| 车标 | - |

<a name="YXaaU"></a>
##### 图片抽取(❌)
<a name="UNF6c"></a>
#### 行业调研报告(文本/无线表格/图片)
<a name="IETdK"></a>
##### 文本抽取(✅)
对于其他格式转换得到的docx解析很差，因为xml中缺少元素信息，造成原始的分段和类型的识别都出现问题<br />![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722690671825-7d10f814-051b-4962-9dfb-ee83a0a37329.png#averageHue=%23e6e7e9&clientId=ue4110d4f-3708-4&from=paste&height=311&id=y515g&originHeight=389&originWidth=705&originalType=binary&ratio=1.125&rotation=0&showTitle=false&size=37997&status=done&style=none&taskId=u95c6a415-e78b-4e47-a1bd-dfe445d5b15&title=&width=564)
```python
page_content='一、驶向2030—汽车行业竞速赛' 
metadata={'source': 'docs/行业研究.docx', 'filename': '行业研究.docx', 'category': 'Title'}

page_content='我们正在经历的，是汽车行业的又   — 核心胜负手变革：“爆款”车辆的'
metadata={'source': 'docs/行业研究.docx',  'filename': '行业研究.docx', 'category': 'Title'}

page_content='一次伟大变革。自19世纪80年代'
metadata={'source': 'docs/行业研究.docx',  'filename': '行业研究.docx', 'category': 'Title'}

```
<a name="KhbOl"></a>
##### 表格提取(❌)
非docx标准表格，由图片+无线表格组成提取不了,会直接分段为普通文字<br />![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722749230562-abcdb005-2187-4ae5-b82c-6cf55480f252.png#averageHue=%23fdfdfd&clientId=u00e935eb-204d-4&from=paste&height=585&id=f22Ca&originHeight=585&originWidth=661&originalType=binary&ratio=1.5&rotation=0&showTitle=false&size=114757&status=done&style=none&taskId=u59ca8a16-7ee1-4298-ac5f-3f148f31294&title=&width=661)<br />![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722749846045-4c7221b3-16cc-468e-a291-e71f9c36e381.png#averageHue=%23fdfdfd&clientId=u00e935eb-204d-4&from=paste&height=864&id=Nvwdg&originHeight=864&originWidth=674&originalType=binary&ratio=1.5&rotation=0&showTitle=false&size=100260&status=done&style=none&taskId=u296f4fd9-7011-4bc8-9984-310df892fcc&title=&width=674)
```python
page_content='图5即便在中低线城市的中型以上细分市场，电动汽车'
metadata={'source': 'docs/行业研究.docx', 
                   'filename': '行业研究.docx', 'category': 'Title', 
                   'emphasized_text_contents': None, 
                   'emphasized_text_tags': None,
                   'page_number': None}

page_content='渗透率也同样实现了巨大提升'
metadata={'source': 'docs/行业研究.docx', 
                   'filename': '行业研究.docx', 'category': 'Title', 
                   'emphasized_text_contents': None, 
                   'emphasized_text_tags': None,
                   'page_number': None}
page_content='电动汽车渗透率 2022年 (1~9月份)'
metadata={'source': 'docs/行业研究.docx', 
                   'filename': '行业研究.docx', 'category': 'Title', 
                   'emphasized_text_contents': None, 
                   'emphasized_text_tags': None,
                   'page_number': None}
page_content='2020年'
metadata={'source': 'docs/行业研究.docx', 
                   'filename': '行业研究.docx', 'category': 'Title', 
                   'emphasized_text_contents': None, 
                   'emphasized_text_tags': None,
                   'page_number': None}
page_content='百分比'
metadata={'source': 'docs/行业研究.docx', 
                   'filename': '行业研究.docx', 'category': 'Title', 
                   'emphasized_text_contents': None, 
                   'emphasized_text_tags': None,
                   'page_number': None}
```
<a name="Pc8pf"></a>
##### 图片提取(❌)
<a name="D9fzF"></a>
## RagFlow-DeepDoc
<a name="SnNNA"></a>
### 场景实践
<a name="NhVsG"></a>
#### 简历抽取-复杂格式(❌)
完全提取不出任何文本信息，因为简历格式太复杂了，unstructure无法处理
<a name="U0I6t"></a>
#### 政府前瞻规划(目录/文本/图片/表格)
<a name="hqQEw"></a>
##### 文本抽取(✅)
因为本身由docx写的，xml信息足够丰富，文本的提取比较好，且分块比较合理，表格抽取也能解决跨页的问题<br />![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722685211498-5e891289-feb3-4b63-bf31-b7f5b18b28b6.png#averageHue=%23eaeaea&clientId=ue4110d4f-3708-4&from=paste&height=548&id=dG6YQ&originHeight=1008&originWidth=826&originalType=binary&ratio=1.125&rotation=0&showTitle=false&size=113031&status=done&style=none&taskId=ubd220b12-d991-40d3-8b17-12d7171e756&title=&width=449.22222900390625)<br />这里因为识别标题的时候没有解析到Heading 标识，所以将上一次识别到的标题到下一个识别到的标题之前的文本都当成一个段落了,避免文案太多，这里做了"..."省略
```python
page_content= """
一、现状基础及发展形势
（一）发展成效
“十三五”期间，杭州市积极利用现有汽车产业基础，坚持市场主导与政府扶持相结合、推广应用和设施配套相结合、整车发展与零部件生产相结合、...。
1.总体规模保持稳定，零部件占比较高。...。
2.空间布局基本形成,集聚效应较为明显。...
3.创新能力显著提升，智能化水平进一步提高。...。
4.智能网联汽车产业加快发展，产业生态基本形成。“十三五”期间，杭州市充分发挥数字经济优势，...。

5.新能源汽车推广卓有成效，配套设施逐步完善。“十三五”期间，...。
6.政策扶持力度不断完善，本地配套率逐步提升。2017年，...。
（二）存在问题
虽然“十三五”期间杭州市汽车产业发展取得了显著成效，...。
（三）发展形势
1.传统汽车行业步入转型升级关键期。近年来，...。
2.新能源汽车行业进入快速发展阶段。国家、地方政策双轮驱动，...。
3.智能汽车产业呈现提速发展态势。5G通讯、感知、人工智能、大数据、...。
4.跨界合作成为新常态。智能网联汽车是汽车工业、人工智能及电子通信等多领域融合的新兴业态，...。"""
```
<a name="SipQh"></a>
##### 表格抽取(✅)
![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722683188399-ba9f1ad8-2c93-4f54-87ec-0ee8b9f0a31c.png#averageHue=%23ececec&clientId=ue4110d4f-3708-4&from=paste&height=568&id=LqD1A&originHeight=1017&originWidth=759&originalType=binary&ratio=1.125&rotation=0&showTitle=false&size=90232&status=done&style=none&taskId=u2b1b12d1-fdef-403e-9cbf-880faaac049&title=&width=423.66668701171875)<br />表格的html格式获取没有问题
```html
<table>
  <tr>
    <td>专栏4：突破智能网联汽车关键技术和平台</td>
  </tr>
  <tr>
    <td>1.环境感知技术：重点突破雷达探测、机器视觉、车辆姿态感知、乘员状态感知和协同感知技术，支持杰华特、大立微电子、兰特普等企业在车规级毫米波雷达、红外夜视、激光雷达等专业特定领域实现技术突破。

2.规划决策技术：加强在边缘计算、大数据、人工智能、多源异构计算、云计算模型库建设、云端数据分级共享技术等方面进行技术和产业布局，强化云端汽车大脑运算和决策能力，突破多车协同规划和智能决策技术。

3.控制执行技术：重点突破下一代智能汽车的单车智能控制和多车协同控制技术，搭建适用于不同级别智能汽车控制策略开发的测试仿真平台，探索深度学习与增强学习在智能汽车决策控制技术开发中的应用。

4.智能汽车软件平台：针对智能汽车应用的高安全、高可靠、强实时等需求，攻克面向异构多处理硬件平台的智能汽车操作系统关键技术，满足实时控制、高性能计算和安全防护的要求。

5.车联网云控平台：建立车联网系统架构，打通车端、路端数据，开发数据应用，支撑多级别的智能驾驶与新一代智能交通发展，服务政府管理、企业研发和用户出行需要。
    </td>
  </tr>
</table>
```
| 专栏2：构建智能网联汽车产业生态 |
| --- |
| 1. 推动智能汽车测试服务。支持市内企业和科研机构建设智能汽车仿真测试与研发平台，提供各类增值及管理服务，实现多主体互利共赢。 |
| 2. 探索车载综合信息服务。利用车载互联网平台，导入地图、商业、旅行、交通等信息服务业务，引导智能汽车企业积极协同阿里巴巴等互联网企业，充分利用云计算、大数据等先进技术，挖掘工作、生活和娱乐等多元化的需求，创新车载信息服务模式，促进智能汽车产业链向后端延伸。 |
| 3. 推进大数据服务。向企业和科研机构开放交通大数据，建设城市数据平台。围绕跨领域大数据的应用，实现智能汽车的商业模式创新、全生命周期的安全管理。 |
| 4. 促进定位服务与高精度地图商业应用。依托高德地图等企业，重点突破高精度定位技术，实现地图数据自动化处理、地图数据质量检查、海量高精度地图数据存储管理等规模化、自动化的服务。 |
| 5. 培育自动驾驶出行服务。鼓励车企与运营服务商合作，开展无人驾驶+共享出行服务。在萧山、滨江、余杭等地率先开展基于无人驾驶汽车的无人公交、无人物流、移动零售、移动办公等新型服务业。拓展车联网商业化空间，挖掘特定场景应用价值。 |
| 6. 发展智能汽车金融保险服务。鼓励保险企业积极探索自动驾驶在路测、试运营以及商业化阶段保险机制，调整保险范围、赔偿机制，创新保险产品。鼓励发展二手车、汽车租赁等金融服务，加快建立智能汽车产业金融支持体系。 |

<a name="AdFqd"></a>
##### 图片抽取(✅)
根据xml解析得到分段里面的图片信息，但是有点图片格式不是这样，而且一个段落可能存在多张图片<br />![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722763313686-20dc1b6f-6294-43c3-b73e-079a0ccc1282.png#averageHue=%2380a1bf&clientId=ub420aeee-35df-4&from=paste&height=477&id=u1306344e&originHeight=973&originWidth=1291&originalType=binary&ratio=1&rotation=0&showTitle=false&size=1289238&status=done&style=none&taskId=uf1c12fbf-2286-4923-9991-5f585cf37bc&title=&width=633)
```html
    def get_picture(self, document, i, paragraph):
        img = paragraph._element.xpath('.//pic:pic')
        if not img:
            return None
        img = img[0]
        embed = img.xpath('.//a:blip/@r:embed')[0]
        related_part = document.part.related_parts[embed]
        image = related_part.image
        image = Image.open(BytesIO(image.blob))
        image.save(f'../output/images/image-{i}.png')
        return image
```
<a name="qIb67"></a>
#### 问界功能手册(目录/文本/表格 /图片)
<a name="ZCGmY"></a>
##### 文本抽取(✅)
进行了标题的提取增强，将标题嵌入到每个文本分段的前方<br />![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722743989467-e22897f7-329f-4571-9be5-c89b0f08f63b.png#averageHue=%23f8f8f6&clientId=u00e935eb-204d-4&from=paste&height=201&id=amMzi&originHeight=201&originWidth=624&originalType=binary&ratio=1.5&rotation=0&showTitle=false&size=13970&status=done&style=none&taskId=u0b1aa38c-3d71-47a5-af51-70cd6005367&title=&width=624)
```python
page_content='用车建议/n/n 在本章中，您可了解驾驶车辆时的注意事项及车辆日常养护，请仔细阅读本部分。'
metadata={}
```
![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722764095704-216c51ba-e7cf-48de-b8da-b772c171803a.png#averageHue=%23f6f6f6&clientId=u9fe93b65-0740-4&from=paste&height=200&id=ucd802c12&originHeight=433&originWidth=1765&originalType=binary&ratio=1&rotation=0&showTitle=false&size=76978&status=done&style=none&taskId=u0434bf7b-f4ea-48f5-b934-f35dfbfa300&title=&width=817)
```python
"""
用车建议
家庭用车建议
老人乘车

带老人出行时，为保障老人乘车安全，请您务必注意以下事项：
适度打开车窗或空调，以保持车内空气新鲜，可预防老人出现头痛、头晕等症状。
请勿将老人单独留在车内。
车辆遇到坑洼或者弯道请减速缓慢通过，避免产生大幅度的晃动，导致老人产生头晕、心慌等症状。
老人在后排乘坐时，建议开启车门儿童锁， 避免老人误开车门。
若您的车辆配备主驾头枕音响，您可在老人休息时开启头枕私享模式，避免音乐、导航播报等吵醒老人。

"""
```
<a name="AYFW6"></a>
##### 表格提取(✅)
![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722743770910-542856e5-2870-483a-b723-d0655b853a24.png#averageHue=%23fafafa&clientId=u00e935eb-204d-4&from=paste&height=301&id=XPheY&originHeight=301&originWidth=690&originalType=binary&ratio=1.5&rotation=0&showTitle=false&size=19250&status=done&style=none&taskId=ub7e52686-9d3b-49bd-9116-687ae20c3aa&title=&width=690)
```python
page_content="""
<table>
  <tr>
    <td> 加油口盖 ( 282 页)</td><td> 全景环视摄像头 ( 172 页)</td>
  </tr>
  <tr>
    <td> 行李支撑架 ( 111 页)</td>
    <td> 车辆牌照位置
    </td>
  </tr>
  <tr>
    <td> 激光雷达</td>
    <td> 超声波雷达</td>
  </tr>
  <tr>
    <td> 侧视摄像头</td>
    <td> 轮胎 ( 299 页)</td>
  </tr>
  <tr>
    <td> 前风挡雨刮 ( 102 页)</td>
    <td> 全景环视摄像头 ( 172 页)</td>
  </tr>
  <tr>
    <td> 前照灯 ( 93 页)</td>
    <td> 车门外把手 ( 63 页)</td>
  </tr>
  <tr>
    <td> 车标</td>
    <td>—</td>
  </tr>
</table>"""}
```
| 加油口盖 ( 282 页) | 全景环视摄像头 ( 172 页) |
| --- | --- |
| 行李支撑架 ( 111 页) | 车辆牌照位置 |
| 激光雷达 | 超声波雷达 |
| 侧视摄像头 | 轮胎 ( 299 页) |
| 前风挡雨刮 ( 102 页) | 全景环视摄像头 ( 172 页) |
| 前照灯 ( 93 页) | 车门外把手 ( 63 页) |
| 车标 | - |

<a name="XLqmA"></a>
##### 图片抽取(✅)
![image-113.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722765363102-a66a237a-7f4e-4ecf-bc34-1f05e91289e0.png#averageHue=%23979f91&clientId=u9fe93b65-0740-4&from=paste&height=512&id=u02dba9ef&originHeight=512&originWidth=832&originalType=binary&ratio=1&rotation=0&showTitle=false&size=348593&status=done&style=none&taskId=ufac48b91-a635-4a17-8e60-ad51337020d&title=&width=832)
<a name="AClKw"></a>
#### 行业调研报告(❌)
缺少目录信息，无法进行解析
<a name="A2YTP"></a>
## 优化项
<a name="bwhhC"></a>
### 图片及关联上下文提取(✅)
直接使用docx库来提取docx中的图片，以及融合上下文信息，同时使用Langchain-chat-chat的方案处理纯文本得到不错的原始分段，参考UnstructuredWordDocumentLoader实现<br />![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722701196054-c9b292f2-0e9c-4c15-aad6-10ec284c1c3b.png#averageHue=%23f6f6f6&clientId=ue4110d4f-3708-4&from=paste&height=782&id=uad2a178a&originHeight=977&originWidth=1475&originalType=binary&ratio=1.125&rotation=0&showTitle=false&size=453397&status=done&style=none&taskId=u9be574f0-bae1-44d7-be73-fb3f6ed7ec7&title=&width=1180)<br />![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722701720565-ad399766-3279-43b7-bc9c-008ee25161c0.png#averageHue=%2381a1bf&clientId=ue4110d4f-3708-4&from=paste&height=762&id=u16fa0931&originHeight=952&originWidth=1269&originalType=binary&ratio=1.125&rotation=0&showTitle=false&size=868336&status=done&style=none&taskId=ube6b1874-a968-4b56-ae98-862643f7301&title=&width=1015.2)
```python
Image 0 
Context:发展节能与新能源汽车是我国从汽车大国迈向汽车强国的必由之路，是应对气候变化、推动绿色发展的战略举措。
当前，全球新一轮科技革命和产业变革蓬勃发展为汽车产业转型提供了广阔的空间，电动化、智能化、网联化、共享化成为汽车产业发展的潮流和趋势。
汽车产业是杭州市深入实施“新制造业计划”的重点领域，杭州市应抢抓“十四五”汽车产业转型升级的关键窗口期，推进汽车产业高质量发展，着力实现换道超车。
4.智能网联汽车产业加快发展，产业生态基本形成。
“十三五”期间，杭州市充分发挥数字经济优势，大力推进智能网联汽车核心技术研发和产业化应用。
成功搭建智能网联汽车共性研究平台，成立浙江省智能汽车及关键零部件产业创新中心和浙江省智能网联汽车创新中心，为杭州市传统汽车零部件产业转型升级、新兴智能网联汽车零部件产业化提供研究平台。
智能网联汽车关键技术不断突破，激光雷达、毫米波雷达、高清摄像头等关键传感器制造水平国内领先，阿里集团旗下斑马网络开发的具有自主知识产权的AliOS车载操作系统已搭载近200万辆智能汽车。
智能网联车测试示范应用取得新进展，杭州云栖小镇成功申请为国家级智能网联示范区，阿里巴巴等6家公司获得智能网联汽车道路测试牌照，开放5条公共测试道路。
5.新能源汽车推广卓有成效，配套设施逐步完善。
“十三五”期间，杭州市持续出台新能源汽车推广应用财政支持政策，鼓励消费者购买新能源汽车，支持各类资本参与建设充换电设施。
截至2020年，全市累计推广新能源汽车21.6万辆，主城区内公交车实现100%电动化，新能源汽车推广成效全国领先。
截至2020年，全市累计建成公用和共用充电桩14889个，提前完成浙江省“十三五”发展规划建成公用充电桩3000个的目标任务，各项指标均列全国城市前列。
早晚交通错峰限行区域内公用充电服务半径缩小至0.9公里，有效满足了新能源汽车的应急充电需求。
依托新能源汽车充电设施智能化管理系统和“杭州e充”App，积极推进“充电设施+互联网”，为用户提供可靠充电服务保障，成为城市交通绿色低碳化的重要组成部分。
```
```python
from docx import Document, ImagePart

from io import BytesIO
from PIL import Image
import os

from rapidocr_onnxruntime import RapidOCR

file_path = f"docs/新能源汽车发展政府规划.docx"
# 加载 .docx 文件
doc = Document(file_path)

# 存储图片及其上下文信息
images_context = []


if __name__ == '__main__':
    ocr = RapidOCR()
    # 直接访问 related_parts
    for rId, part in doc.part.related_parts.items():
        if isinstance(part, ImagePart):
            # 获取图片数据
            image_data = part.blob
            # 保存图片
            image_id = len(images_context)
            # 确保输出目录存在
            output_dir = f'output/images'
            os.makedirs(output_dir, exist_ok=True)

            # 确定图片的原始格式
            image = Image.open(BytesIO(image_data))
            format = image.format.lower()
            # 保存图片
            image_path = f'{output_dir}/image_{image_id}.{format}'
            # 将原始图片的数据复制到新对象
            # 确定图片格式
            format = image.format.lower()
            image.save(image_path)

            # 记录图片的前后文
            context_text = ''
            # 查找图片所在位置
            for i, paragraph in enumerate(doc.paragraphs):
                if paragraph._p.xpath('.//a:graphic'):
                    if paragraph.text.strip():
                        context_text = paragraph.text
                        continue
                    # 向前查找文本
                    if i > 0:
                        context_text += doc.paragraphs[i - 1].text
                    # 向后查找文本
                    if i < len(doc.paragraphs) - 1:
                        context_text += doc.paragraphs[i + 1].text
                    break
            # 保存图片及其上下文
            images_context.append({
                "image_id": image_id,
                "context_text": context_text
            })

    # 输出图片及其上下文信息
    for info in images_context:
        context = info['context_text'].replace('。', '。\n')
        print(f"""Image {info['image_id']} 
Context:{context}""")



```

<a name="Amk4o"></a>
### 标题树状结构生成(✅)
需要特殊的处理，应该直接由pdf来做视觉上的识别和知识关系上的处理<br />可以看到，处理后能够得到当前标题的层级结构以及段落的文本<br />![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722822652944-7ee61a0c-e443-4d61-92a4-4b185a9bbe94.png#averageHue=%23fdfdfd&clientId=u24c74686-dda3-4&from=paste&height=676&id=u80e5386f&originHeight=1352&originWidth=2766&originalType=binary&ratio=2&rotation=0&showTitle=false&size=500291&status=done&style=none&taskId=u36589eac-8de8-4263-a632-7b3b2e87068&title=&width=1383)
```python
{'type': 'paragraph', 
 'page_number': 1, 
 'filename': '../docs/问界使用说明书_部分.docx', 
 'title_stack': ['用车建议', '行车注意事项', '长途驾驶'], 
 'text': """在开车长途驾驶之前请您务必注意以下事项：为了保证您的出行安全，
 长途驾驶前请先检查车辆状态。提前了解出行路线，确保车辆电量、油量充足。
 途中休息时，您可以使用小憩模式功能来缓解长途驾驶的疲劳，避免疲劳驾驶。
 长途旅行，带好水及必要的食物，及时补充能量。""", 
 'title_level': [1, 2, 4]}
```
![image.png](https://cdn.nlark.com/yuque/0/2024/png/45057756/1722823643006-9847e687-6e12-4ebb-b237-c84b5e47bf36.png#averageHue=%23f6f6f6&clientId=u24c74686-dda3-4&from=paste&height=628&id=u1dd6916a&originHeight=1256&originWidth=1230&originalType=binary&ratio=2&rotation=0&showTitle=false&size=378367&status=done&style=none&taskId=uf2df4967-3f10-46f3-853e-ea5a98b6d6f&title=&width=615)<br />图片部分:

表格部分:
```python
{'type': 'table', 'page_number': 5, 
 'filename': '../docs/问界使用说明书_部分.docx',
 'title_stack': ['车辆概览', '外观简介', '外观图（一）'], 
 'md': '|加油口盖 ( 282 页) | 全景环视摄像头 ( 172 页)|\n|--- | ---|\n加油口盖 ( 282 页)|全景环视摄像头 ( 172 页)|\n行李支撑架 ( 111 页)|车辆牌照位置|\n激光雷达|超声波雷达|\n侧视摄像头|轮胎 ( 299 页)|\n前风挡雨刮 ( 102 页)|全景环视摄像头 ( 172 页)|\n前照灯 ( 93 页)|车门外把手 ( 63 页)|\n车标|—|\n', 'surrounding_text': {'forward_text': '*画面仅供参考，请以产品实际为准', 'backward_text': None, 'current_text': None}, 'title_level': [1, 2, 5]}
```
| 加油口盖 ( 282 页) | 全景环视摄像头 ( 172 页) |
| --- | --- |
| 加油口盖 ( 282 页) | 全景环视摄像头 ( 172 页) |
| 行李支撑架 ( 111 页) | 车辆牌照位置 |
| 激光雷达 | 超声波雷达 |
| 侧视摄像头 | 轮胎 ( 299 页) |
| 前风挡雨刮 ( 102 页) | 全景环视摄像头 ( 172 页) |
| 前照灯 ( 93 页) | 车门外把手 ( 63 页) |
| 车标 | — |


<a name="yAgPz"></a>
### 表格嵌套图片

