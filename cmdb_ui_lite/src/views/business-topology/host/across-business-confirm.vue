<!--
 * Tencent is pleased to support the open source community by making 蓝鲸 available.
 * Copyright (C) 2017 Tencent. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 * http://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
-->

<template>
  <section class="across-confirm">
    <h1 class="title">转移主机到其他业务</h1>
    <p class="content">
      所选的<span class="count">{{count}}</span>台主机有<span class="invalid">{{invalidList.length}}</span>台不属于<span>空闲机池</span>，不能移除至其他业务，将会自动忽略
    </p>
    <invalid-list :title="'以下主机不能移除'" :list="invalidList"></invalid-list>
    <div class="flex-spacer"></div>
    <div class="footer">
      <bk-button theme="primary" @click="next">下一步</bk-button>
      <bk-button class="ml10" theme="default" @click="cancel">取消</bk-button>
    </div>
  </section>
</template>

<script>
  import InvalidList from './invalid-list'
  export default {
    name: 'across-business-confirm',
    components: {
      InvalidList
    },
    props: {
      count: {
        type: Number,
        default: 0
      },
      invalidList: {
        type: Array,
        default: () => ([])
      }
    },
    methods: {
      next() {
        this.$emit('confirm')
      },
      cancel() {
        this.$emit('cancel')
      }
    }
  }
</script>

<style lang="scss" scoped>
    .across-confirm {
        display: flex;
        flex-direction: column;
        height: var(--height, 430px);
        min-height: 300px;
        .title {
            flex: none;
            text-align: center;
            margin: 45px 0 17px;
            line-height: 32px;
            font-size:24px;
            font-weight: normal;
            color: #313238;
        }
        .content {
            flex: none;
            padding: 0 20px;
            line-height: 20px;
            font-size:14px;
            color: $textColor;
            .count {
                font-weight: bold;
                color: $successColor;
                padding: 0 4px;
            }
            .invalid {
                font-weight: bold;
                color: $dangerColor;
                padding: 0 4px;
            }
        }
        .flex-spacer {
            flex: 1;
            min-height: 0;
        }
        .footer {
            flex: none;
            display: flex;
            margin-top: auto;
            align-items: center;
            justify-content: flex-end;
            height: 50px;
            padding: 8px 20px;
            border-top: 1px solid $borderColor;
            background-color: #FAFBFD;
        }
    }
</style>
