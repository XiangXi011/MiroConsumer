# P1-3: 默认消费者画像扩充到 15-20 个

## 目标
扩充 `backend/app/services/consumer/data/default_personas.json`，从当前 8 个画像增加到 15-20 个，覆盖不少于 5 个社区。

## 当前状态
文件仅包含 8 个画像（M01-M08），覆盖 3 个社区（caregivers, analysts, social_shoppers）。

## 要求

### 必须做
1. 读取现有 `default_personas.json`，理解字段结构
2. 新增 7-12 个画像，覆盖以下典型中国消费者类型：
   - 银发族（60+岁，保守型）
   - Z 世代学生（18-24，价格敏感+社交驱动）
   - 下沉市场消费者（三四线城市）
   - 高收入精致生活追求者
   - 小镇青年
   - 健康养生关注者
   - 直播购物重度用户
3. 新增社区：至少增加 `elderly`、`gen_z`、`health_conscious` 等
4. 保持现有 M01-M08 不变
5. 所有新画像字段必须符合现有 schema

### 不要做什么
- 不删除或修改现有 M01-M08
- 不引入不可解释的随机数据
- 不修改 persona loader 代码

## 验收标准
1. 默认画像数量 ≥ 15
2. 社区数 ≥ 5
3. 新画像能通过现有 loader 校验
4. `python -c "import json; d=json.load(open('default_personas.json')); print(len(d['personas']), len(set(p.get('community','') for p in d['personas'])))"` 输出数量正确

## 环境
- 工作目录: `/Users/xiangdong/MiroConsumer-phase5`
- 目标文件: `backend/app/services/consumer/data/default_personas.json`
