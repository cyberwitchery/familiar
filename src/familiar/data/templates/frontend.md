# react frontend

this is a react project. write clean, accessible, and performant components.

## commands

```
npm run lint
npm run typecheck
npm test
```

adjust to match the project's package.json scripts.

## constraints

before making changes, check:
- which package manager? (npm, yarn, pnpm)
- component library or design system in use?
- styling approach? (css modules, tailwind, styled-components)
- framework? (Next.js, Remix, Vite, CRA)

STOP and ask before:
- adding dependencies
- changing shared components
- modifying build configuration

do not:
- use `any` in TypeScript
- leave console.log in production code
- ignore accessibility (alt text, labels, keyboard nav)
- create components over ~100 lines without splitting them
- use `useEffect` for derived state
- fetch in useEffect without cleanup

prefer:
- function components with hooks
- composition over prop drilling
- controlled inputs
- semantic HTML over divs with roles
- colocate component, styles, and tests

## accessibility

every interactive component needs:
- keyboard navigation
- visible focus states
- ARIA attributes where semantic HTML isn't enough
- color contrast meeting WCAG AA

## testing

use React Testing Library. test behavior, not implementation:
- use accessible queries (`getByRole`, `getByLabelText`)
- avoid `container.querySelector`
- don't test internal state

## verification

```
npm run lint && npm run typecheck && npm test
```
