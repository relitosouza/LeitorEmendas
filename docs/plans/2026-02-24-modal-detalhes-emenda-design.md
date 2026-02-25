# Design: Modal de Detalhes da Emenda no Histórico

**Data**: 2026-02-24

## Objetivo

Ao clicar em uma linha da tabela de histórico de emendas, abrir um modal centralizado exibindo detalhes da emenda: Município, Destino e Valor.

## Decisões

- **Abordagem**: HTML/JS puro + Tailwind (sem dependências extras), consistente com o projeto
- **Gatilho**: Clique na linha da tabela do histórico
- **Estilo**: Modal centralizado com overlay escuro

## Especificação

### Conteúdo do Modal

Três campos exibidos no modal:

| Campo      | Fonte            | Apresentação                    |
|------------|------------------|---------------------------------|
| Município  | `row.municipio`  | Label cinza + valor em texto    |
| Destino    | `row.destino`    | Label cinza + valor em texto    |
| Valor      | `row.valor_raw`  | Label cinza + valor em BRL, destaque azul |

### Estrutura Visual

```
+------------------------------------------+
|          OVERLAY (bg-black/50)            |
|    +--------------------------------+     |
|    |  [X]          Detalhes         |     |
|    |--------------------------------|     |
|    |  Município                     |     |
|    |  São Paulo                     |     |
|    |                                |     |
|    |  Destino                       |     |
|    |  Hospital Municipal XYZ        |     |
|    |                                |     |
|    |  Valor                         |     |
|    |  R$ 150.000,00                 |     |
|    +--------------------------------+     |
+------------------------------------------+
```

### Comportamento

- **Abrir**: Clique em qualquer linha da tabela `#tabelaEmendas`
- **Fechar**: Clique no botão X, clique no overlay, ou tecla Escape
- **Animação**: Fade-in do overlay + scale do card
- **Responsivo**: `max-w-md` no desktop, quase full-width no mobile

### Classes Tailwind

- Overlay: `fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center`
- Card: `bg-white rounded-2xl shadow-2xl p-6 mx-4 max-w-md w-full`
- Labels: `text-xs text-gray-500 uppercase tracking-wider`
- Valores: `text-lg font-semibold text-gray-900`
- Valor (BRL): `text-2xl font-bold text-blue-600`
- Botão X: `text-gray-400 hover:text-gray-600`

### Implementação

Alterações necessárias apenas em `index.html`:

1. Adicionar HTML do modal após a seção do histórico
2. Adicionar funções `openEmendaModal(data)` e `closeEmendaModal()`
3. No loop `data.historico.forEach`, adicionar `onclick` nas linhas `<tr>` passando os dados da emenda
4. Adicionar listener de tecla Escape para fechar

Nenhuma alteração no backend (`app.py`) é necessária — todos os dados já estão disponíveis no response da API.
