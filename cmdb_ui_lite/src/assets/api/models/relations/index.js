import instanceRelations from './instance.json'

export const allRelations = [
  ...(instanceRelations?.relations || [])
]

export default allRelations
