export default {
  computed: {
    $APP() {
      return {
        height: this.$store.state.global.appHeight
      }
    }
  }
}
